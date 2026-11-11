"""Parking space detection with OpenCV.

DETECTION ALGORITHM (``EdgeDensityDetector``)
---------------------------------------------
1. Convert the whole frame to grayscale and blur it slightly (removes noise).
2. Run the Canny edge detector once on the whole frame.
3. For every configured parking space, take its rectangle, shrink it by a small
   margin (so painted lines on the border are ignored) and measure the
   *edge density*: ``edge pixels / total pixels`` inside the rectangle.
4. Empty asphalt is mostly smooth, so it has few edges. A car has windows,
   panels, lights and outlines, so it has many edges.
   ``edge density >= threshold``  ->  "occupied", otherwise "vacant".

LIMITATIONS (please read)
-------------------------
This is a basic image-processing method. It has NOT been validated on real
parking-lot footage, so no real-world accuracy is claimed. Expect problems with:
  * Lighting: night, glare, low sun and strong shadows add or hide edges.
  * Shadows and surface texture: cracks, puddles, leaves, oil stains, gravel and
    painted markings can look "busy" and be wrongly marked occupied.
  * Plain objects: a smooth, single-colour car (or a very dark one at night)
    can have few edges and be wrongly marked vacant.
  * Camera angle: spaces must be given in the pixel coordinates of a fixed
    camera. If the camera moves, every rectangle must be re-configured. Cars in
    neighbouring spaces can overlap a rectangle when seen from a low angle.
  * Weather: rain, snow and fog change the edge pattern.
  * The threshold is camera-specific and must be calibrated on your own images.

REPLACING IT WITH YOLO LATER
----------------------------
Everything else in the project talks to the ``BaseDetector`` interface only.
To use a trained YOLO model, write a class that inherits ``BaseDetector`` and
implements ``detect(image, regions)`` (run the model, then mark a space
"occupied" if a detected vehicle box overlaps the space enough), and return it
from ``get_detector()`` below. No endpoint, schema or database code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Sequence

import cv2
import numpy as np

from app.config import settings
from app.models import STATUS_OCCUPIED, STATUS_VACANT

COLOR_OCCUPIED = (0, 0, 255)  # red   (OpenCV uses BGR order)
COLOR_VACANT = (0, 255, 0)  # green
COLOR_UNKNOWN = (160, 160, 160)  # grey: space could not be analysed


@dataclass(frozen=True)
class SpaceRegion:
    """A parking space rectangle in image pixels."""

    id: int
    name: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DetectionResult:
    """Detector output for one space. ``status`` is None if it was skipped."""

    space_id: int
    status: Optional[str]
    score: Optional[float] = None
    note: Optional[str] = None


class BaseDetector(ABC):
    """Interface every detector (edge-based now, YOLO later) must follow."""

    name: str = "base"

    @abstractmethod
    def detect(
        self, image: np.ndarray, regions: Sequence[SpaceRegion]
    ) -> list[DetectionResult]:
        """Return one ``DetectionResult`` per region, in the same order."""


class EdgeDensityDetector(BaseDetector):
    name = "edge_density"

    def __init__(
        self,
        edge_threshold: float = 0.015,
        roi_margin_ratio: float = 0.08,
        min_roi_pixels: int = 100,
        min_visible_fraction: float = 0.5,
        blur_kernel: int = 5,
        canny_low: int = 50,
        canny_high: int = 150,
    ) -> None:
        self.edge_threshold = edge_threshold
        self.roi_margin_ratio = roi_margin_ratio
        self.min_roi_pixels = min_roi_pixels
        self.min_visible_fraction = min_visible_fraction
        self.blur_kernel = blur_kernel
        self.canny_low = canny_low
        self.canny_high = canny_high

    def _edges(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            gray = image
        elif image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        k = self.blur_kernel if self.blur_kernel % 2 == 1 else self.blur_kernel + 1
        blurred = cv2.GaussianBlur(gray, (k, k), 0)
        return cv2.Canny(blurred, self.canny_low, self.canny_high)

    def detect(
        self, image: np.ndarray, regions: Sequence[SpaceRegion]
    ) -> list[DetectionResult]:
        img_h, img_w = image.shape[:2]
        edges = self._edges(image)
        results: list[DetectionResult] = []

        for r in regions:
            margin_x = int(r.width * self.roi_margin_ratio)
            margin_y = int(r.height * self.roi_margin_ratio)
            x0, y0 = r.x + margin_x, r.y + margin_y
            x1, y1 = r.x + r.width - margin_x, r.y + r.height - margin_y
            full_area = max((x1 - x0) * (y1 - y0), 1)

            # Clip to the image so spaces near/outside the border cannot crash.
            cx0, cy0 = max(x0, 0), max(y0, 0)
            cx1, cy1 = min(x1, img_w), min(y1, img_h)
            visible_area = max(cx1 - cx0, 0) * max(cy1 - cy0, 0)

            if (
                visible_area < self.min_roi_pixels
                or visible_area / full_area < self.min_visible_fraction
            ):
                results.append(
                    DetectionResult(
                        r.id,
                        None,
                        None,
                        "Space is outside (or mostly outside) the image; skipped.",
                    )
                )
                continue

            roi = edges[cy0:cy1, cx0:cx1]
            score = float(np.count_nonzero(roi)) / float(roi.size)
            status = STATUS_OCCUPIED if score >= self.edge_threshold else STATUS_VACANT
            results.append(DetectionResult(r.id, status, round(score, 4)))

        return results


@lru_cache(maxsize=1)
def get_detector() -> BaseDetector:
    """Select the configured detection engine.

    PARKING_DETECTOR=yolo enables the AI vehicle detector. Set it to edge
    to use the lightweight OpenCV fallback without downloading YOLO weights.
    """
    engine = settings.detector.strip().lower()
    if engine == "yolo":
        from ai.yolo_detector import YoloParkingDetector
        return YoloParkingDetector(model_path=settings.yolo_model)
    if engine == "edge":
        return EdgeDensityDetector(
            edge_threshold=settings.edge_threshold,
            roi_margin_ratio=settings.roi_margin_ratio,
        )
    raise ValueError("PARKING_DETECTOR must be either 'yolo' or 'edge'.")


def draw_annotations(
    image: np.ndarray,
    items: Sequence[tuple[SpaceRegion, Optional[str]]],
) -> np.ndarray:
    """Return a copy of ``image`` with red (occupied) / green (vacant) boxes.

    A ``None`` status (space not analysed) is drawn in grey.
    """
    if image.ndim == 2:
        canvas = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        canvas = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        canvas = image.copy()

    occupied = vacant = 0
    for region, status in items:
        if status == STATUS_OCCUPIED:
            color, occupied = COLOR_OCCUPIED, occupied + 1
        elif status == STATUS_VACANT:
            color, vacant = COLOR_VACANT, vacant + 1
        else:
            color = COLOR_UNKNOWN
        p1 = (region.x, region.y)
        p2 = (region.x + region.width, region.y + region.height)
        cv2.rectangle(canvas, p1, p2, color, 2)
        label_y = region.y - 6 if region.y > 16 else region.y + region.height + 14
        cv2.putText(
            canvas,
            region.name,
            (region.x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    banner = f"Occupied: {occupied}  Vacant: {vacant}"
    banner_pos = (8, canvas.shape[0] - 10)  # bottom-left, away from space labels
    cv2.putText(
        canvas, banner, banner_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA
    )
    cv2.putText(
        canvas,
        banner,
        banner_pos,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return canvas
