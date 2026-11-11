"""Business logic: summary maths, upload handling, image/video/simulated updates.

The routers stay thin and call the functions in this file. These functions use
``crud.py`` for the database and ``detector.py`` for the image analysis.
"""

import os
import random
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.detector import (
    BaseDetector,
    DetectionResult,
    SpaceRegion,
    draw_annotations,
    get_detector,
)
from app.models import STATUS_OCCUPIED, STATUS_VACANT, ParkingSpace
from app.schemas import (
    DetectionResponse,
    ParkingSummary,
    SpaceDetectionResult,
    VideoDetectionResponse,
)

# --------------------------------------------------------------------------- #
# Errors (the router converts these into HTTP status codes)
# --------------------------------------------------------------------------- #


class ServiceError(Exception):
    """Base class for expected, user-facing errors."""


class UnsupportedMediaError(ServiceError):  # -> 415
    pass


class UploadTooLargeError(ServiceError):  # -> 413
    pass


class InvalidMediaError(ServiceError):  # -> 400
    pass


class NoSpacesConfiguredError(ServiceError):  # -> 400
    pass


# --------------------------------------------------------------------------- #
# Summary calculation
# --------------------------------------------------------------------------- #


def calculate_summary(total: int, occupied: int) -> ParkingSummary:
    """Apply the project formulas. Safe when ``total`` is zero.

    Available = Total - Occupied
    Occupancy %    = Occupied  / Total * 100
    Availability % = Available / Total * 100
    """
    occupied = max(0, min(occupied, total))
    available = total - occupied
    if total == 0:
        occupancy = availability = 0.0
    else:
        occupancy = round(occupied / total * 100, 2)
        availability = round(available / total * 100, 2)
    return ParkingSummary(
        total_spaces=total,
        occupied_spaces=occupied,
        available_spaces=available,
        occupancy_percentage=occupancy,
        availability_percentage=availability,
    )


def get_summary(db: Session) -> ParkingSummary:
    """Always recalculated from the database, so it can never be out of date."""
    total, occupied = crud.count_spaces(db)
    return calculate_summary(total, occupied)


# --------------------------------------------------------------------------- #
# Upload validation
# --------------------------------------------------------------------------- #

_MEDIA_RULES = {
    "image": {
        "extensions": {".jpg", ".jpeg", ".png", ".bmp", ".webp"},
        "content_types": {
            "image/jpeg",
            "image/png",
            "image/bmp",
            "image/x-ms-bmp",
            "image/webp",
        },
        "max_bytes": lambda: settings.max_image_size_mb * 1024 * 1024,
    },
    "video": {
        "extensions": {".mp4", ".avi", ".mov", ".mkv", ".webm"},
        "content_types": {
            "video/mp4",
            "video/x-msvideo",
            "video/avi",
            "video/quicktime",
            "video/x-matroska",
            "video/webm",
        },
        "max_bytes": lambda: settings.max_video_size_mb * 1024 * 1024,
    },
}
_GENERIC_CONTENT_TYPES = {"", "application/octet-stream"}


def _validate_upload_type(file: UploadFile, kind: str) -> str:
    """Check extension and content type. Returns the lower-case extension."""
    rules = _MEDIA_RULES[kind]
    ext = Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "").lower()
    if ext not in rules["extensions"]:
        allowed = ", ".join(sorted(rules["extensions"]))
        raise UnsupportedMediaError(
            f"Unsupported {kind} file type '{ext or 'none'}'. Allowed: {allowed}."
        )
    if (
        content_type not in rules["content_types"]
        and content_type not in _GENERIC_CONTENT_TYPES
    ):
        raise UnsupportedMediaError(
            f"Unsupported content type '{content_type}' for a {kind} upload."
        )
    return ext


def read_validated_upload(file: UploadFile, kind: str) -> bytes:
    """Validate type and size, then return the file bytes (used for images)."""
    _validate_upload_type(file, kind)
    limit = _MEDIA_RULES[kind]["max_bytes"]()
    data = bytearray()
    while chunk := file.file.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > limit:
            raise UploadTooLargeError(
                f"The {kind} is larger than the {limit // (1024 * 1024)} MB limit."
            )
    if not data:
        raise InvalidMediaError("The uploaded file is empty.")
    return bytes(data)


def save_video_upload(file: UploadFile) -> Path:
    """Validate a video upload and store it in a temporary file.

    OpenCV reads videos from a path, so the upload must be written to disk. The
    caller must delete the returned file (``process_video`` callers do this).
    """
    ext = _validate_upload_type(file, "video")
    limit = _MEDIA_RULES["video"]["max_bytes"]()
    fd, tmp_name = tempfile.mkstemp(suffix=ext, prefix="parking_upload_")
    tmp_path = Path(tmp_name)
    written = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                if written > limit:
                    raise UploadTooLargeError(
                        f"The video is larger than the {limit // (1024 * 1024)} MB limit."
                    )
                out.write(chunk)
        if written == 0:
            raise InvalidMediaError("The uploaded file is empty.")
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path


def decode_image(data: bytes) -> np.ndarray:
    """Turn uploaded bytes into an OpenCV image or raise ``InvalidMediaError``."""
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise InvalidMediaError("The file is not a valid, readable image.")
    return image


# --------------------------------------------------------------------------- #
# Processed-image helpers
# --------------------------------------------------------------------------- #


def encode_png(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ServiceError("Could not encode the processed image.")
    return buffer.tobytes()


def save_processed_image(image: np.ndarray) -> str:
    """Save an annotated image in ``processed_images/`` and return its file name."""
    out_dir = Path(settings.processed_images_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
    )
    (out_dir / filename).write_bytes(encode_png(image))
    return filename


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #


@dataclass
class DetectionOutcome:
    response: DetectionResponse
    annotated_image: np.ndarray


def _regions(spaces: list[ParkingSpace]) -> list[SpaceRegion]:
    return [SpaceRegion(s.id, s.name, s.x, s.y, s.width, s.height) for s in spaces]


def _require_spaces(db: Session) -> list[ParkingSpace]:
    spaces = crud.get_spaces(db)
    if not spaces:
        raise NoSpacesConfiguredError(
            "No parking spaces are configured. Add spaces with "
            "POST /api/parking/spaces first."
        )
    return spaces


def _build_outcome_parts(
    db: Session,
    detector: BaseDetector,
    results: list[DetectionResult],
    changed_ids: set[int],
) -> tuple[list[SpaceDetectionResult], list[str], list[tuple[SpaceRegion, Optional[str]]]]:
    """Combine saved statuses with detector scores for the API response."""
    spaces = crud.get_spaces(db)
    by_id = {r.space_id: r for r in results}
    out: list[SpaceDetectionResult] = []
    warnings: list[str] = []
    annotate: list[tuple[SpaceRegion, Optional[str]]] = []
    for region, space in zip(_regions(spaces), spaces):
        res = by_id.get(space.id)
        skipped = res is None or res.status is None
        if skipped:
            warnings.append(
                f"{space.name} (id {space.id}): "
                f"{res.note if res and res.note else 'not analysed'}"
            )
        out.append(
            SpaceDetectionResult(
                space_id=space.id,
                name=space.name,
                status=space.status,
                occupancy_score=None if res is None else res.score,
                changed=space.id in changed_ids,
            )
        )
        annotate.append((region, None if skipped else space.status))
    return out, warnings, annotate


def process_image(
    db: Session, image: np.ndarray, detector: Optional[BaseDetector] = None
) -> DetectionOutcome:
    """Detect every space in one image, save changes, return the response."""
    detector = detector or get_detector()
    spaces = _require_spaces(db)
    results = detector.detect(image, _regions(spaces))

    new_statuses = {r.space_id: r.status for r in results if r.status is not None}
    changed = set(crud.apply_statuses(db, new_statuses))

    items, warnings, annotate = _build_outcome_parts(db, detector, results, changed)
    response = DetectionResponse(
        detector=detector.name,
        spaces_processed=sum(1 for r in results if r.status is not None),
        status_changes=len(changed),
        results=items,
        summary=get_summary(db),
        warnings=warnings,
    )
    return DetectionOutcome(response, draw_annotations(image, annotate))


class StatusDebouncer:
    """Stops flicker in video: a new status must repeat before it is accepted.

    With ``confirm_frames=1`` every detected change is accepted immediately.
    With ``confirm_frames=3`` a space must look different in 3 analysed frames
    in a row before its saved status changes.
    """

    def __init__(self, current: dict[int, str], confirm_frames: int) -> None:
        self.current = dict(current)
        self.confirm_frames = max(1, confirm_frames)
        self._pending: dict[int, tuple[str, int]] = {}

    def update(self, results: list[DetectionResult]) -> dict[int, str]:
        confirmed: dict[int, str] = {}
        for r in results:
            if r.status is None:
                continue
            if r.status == self.current.get(r.space_id):
                self._pending.pop(r.space_id, None)
                continue
            candidate, count = self._pending.get(r.space_id, (r.status, 0))
            if candidate != r.status:
                count = 0
            count += 1
            if count >= self.confirm_frames:
                confirmed[r.space_id] = r.status
                self.current[r.space_id] = r.status
                self._pending.pop(r.space_id, None)
            else:
                self._pending[r.space_id] = (r.status, count)
        return confirmed


def process_video(
    db: Session,
    video_path: Path,
    frame_interval: Optional[int] = None,
    max_frames: Optional[int] = None,
    confirm_frames: Optional[int] = None,
    detector: Optional[BaseDetector] = None,
) -> tuple[VideoDetectionResponse, np.ndarray]:
    """Analyse every ``frame_interval``-th frame and update the database.

    The database is written only when a space's status really changes, and the
    summary is recalculated from the database at the end.
    Returns the response and the annotated last analysed frame.
    """
    detector = detector or get_detector()
    frame_interval = frame_interval or settings.default_frame_interval
    confirm_frames = confirm_frames or settings.default_confirm_frames
    frame_cap = settings.max_processed_frames
    max_frames = min(max_frames or frame_cap, frame_cap)

    spaces = _require_spaces(db)
    regions = _regions(spaces)
    debouncer = StatusDebouncer({s.id: s.status for s in spaces}, confirm_frames)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise InvalidMediaError("The file is not a valid, readable video.")

    frames_read = frames_processed = 0
    changed_ids: set[int] = set()
    last_frame: Optional[np.ndarray] = None
    last_results: list[DetectionResult] = []
    try:
        while frames_processed < max_frames:
            if not capture.grab():
                break
            frames_read += 1
            if (frames_read - 1) % frame_interval != 0:
                continue
            ok, frame = capture.retrieve()
            if not ok or frame is None:
                continue
            results = detector.detect(frame, regions)
            confirmed = debouncer.update(results)
            changed_ids.update(crud.apply_statuses(db, confirmed))
            last_frame, last_results = frame, results
            frames_processed += 1
    finally:
        capture.release()

    if last_frame is None:
        raise InvalidMediaError("No readable frames were found in the video.")

    items, warnings, annotate = _build_outcome_parts(
        db, detector, last_results, changed_ids
    )
    response = VideoDetectionResponse(
        detector=detector.name,
        spaces_processed=sum(1 for r in last_results if r.status is not None),
        status_changes=len(changed_ids),
        results=items,
        summary=get_summary(db),
        warnings=warnings,
        frames_read=frames_read,
        frames_processed=frames_processed,
        frame_interval=frame_interval,
        confirm_frames=confirm_frames,
    )
    return response, draw_annotations(last_frame, annotate)


# --------------------------------------------------------------------------- #
# Simulation (testing without a camera)
# --------------------------------------------------------------------------- #


def simulate_occupancy(
    db: Session, occupancy_rate: float, seed: Optional[int] = None
) -> DetectionResponse:
    """Randomly mark ``round(rate * total)`` spaces occupied and the rest vacant."""
    spaces = _require_spaces(db)
    rng = random.Random(seed)
    occupied_count = round(occupancy_rate * len(spaces))
    occupied_ids = set(rng.sample([s.id for s in spaces], occupied_count))
    new_statuses = {
        s.id: STATUS_OCCUPIED if s.id in occupied_ids else STATUS_VACANT
        for s in spaces
    }
    changed = set(crud.apply_statuses(db, new_statuses))
    updated = crud.get_spaces(db)
    return DetectionResponse(
        detector="simulation",
        spaces_processed=len(updated),
        status_changes=len(changed),
        results=[
            SpaceDetectionResult(
                space_id=s.id,
                name=s.name,
                status=s.status,
                occupancy_score=None,
                changed=s.id in changed,
            )
            for s in updated
        ],
        summary=get_summary(db),
    )
