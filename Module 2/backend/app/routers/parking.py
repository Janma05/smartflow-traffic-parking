"""REST endpoints under ``/api/parking``."""

import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi import Path as PathParam
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud, services
from app.config import settings
from app.database import get_db
from app.models import ParkingSpace
from app.schemas import (
    DetectionResponse,
    ParkingSpaceCreate,
    ParkingSpaceResponse,
    ParkingSpaceUpdate,
    ParkingSummary,
    SimulationRequest,
    VideoDetectionResponse,
)

router = APIRouter(prefix="/api/parking", tags=["Parking"])

_ERROR_STATUS = {
    services.UnsupportedMediaError: 415,
    services.UploadTooLargeError: 413,
    services.InvalidMediaError: 400,
    services.NoSpacesConfiguredError: 400,
}


def _http_error(exc: services.ServiceError) -> HTTPException:
    return HTTPException(status_code=_ERROR_STATUS.get(type(exc), 400), detail=str(exc))


def _get_space_or_404(db: Session, space_id: int) -> ParkingSpace:
    space = crud.get_space(db, space_id)
    if space is None:
        raise HTTPException(
            status_code=404, detail=f"Parking space with id {space_id} was not found."
        )
    return space


SpaceId = PathParam(..., ge=1, description="Parking space id (a positive integer)")


# --------------------------------------------------------------------------- #
# Parking space CRUD
# --------------------------------------------------------------------------- #
@router.get("/spaces", response_model=list[ParkingSpaceResponse])
def list_spaces(db: Session = Depends(get_db)):
    """Retrieve all parking spaces and their current statuses."""
    return crud.get_spaces(db)


@router.get("/summary", response_model=ParkingSummary)
def parking_summary(db: Session = Depends(get_db)):
    """Total, occupied, available spaces and the two percentages."""
    return services.get_summary(db)


@router.get("/spaces/{space_id}", response_model=ParkingSpaceResponse)
def get_space(space_id: int = SpaceId, db: Session = Depends(get_db)):
    """Retrieve one parking space."""
    return _get_space_or_404(db, space_id)


@router.post("/spaces", response_model=ParkingSpaceResponse, status_code=201)
def create_space(data: ParkingSpaceCreate, db: Session = Depends(get_db)):
    """Register a parking space (name + rectangle in image pixels)."""
    return crud.create_space(db, data)


@router.put("/spaces/{space_id}", response_model=ParkingSpaceResponse)
def update_space(
    data: ParkingSpaceUpdate, space_id: int = SpaceId, db: Session = Depends(get_db)
):
    """Update a space's name, coordinates, size or (manually) its status."""
    space = _get_space_or_404(db, space_id)
    return crud.update_space(db, space, data)


@router.delete("/spaces/{space_id}", status_code=204, response_class=Response)
def delete_space(space_id: int = SpaceId, db: Session = Depends(get_db)):
    """Delete a parking space."""
    crud.delete_space(db, _get_space_or_404(db, space_id))
    return Response(status_code=204)


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #
@router.post("/detect/image", response_model=DetectionResponse)
def detect_image(
    file: UploadFile = File(..., description="Parking-lot image (jpg, png, bmp, webp)"),
    return_image: bool = Query(
        False, description="true = respond with the annotated PNG instead of JSON"
    ),
    db: Session = Depends(get_db),
):
    """Detect occupied/vacant spaces in an uploaded image and save the result.

    The annotated image (red = occupied, green = vacant) is saved and its URL is
    returned in ``processed_image_url``. With ``return_image=true`` the PNG itself
    is returned and the numbers are placed in ``X-*`` response headers.
    """
    try:
        data = services.read_validated_upload(file, "image")
        image = services.decode_image(data)
        outcome = services.process_image(db, image)
    except services.ServiceError as exc:
        raise _http_error(exc) from exc

    filename = services.save_processed_image(outcome.annotated_image)
    outcome.response.processed_image_url = f"/api/parking/processed/{filename}"

    if return_image:
        summary = outcome.response.summary
        return Response(
            content=services.encode_png(outcome.annotated_image),
            media_type="image/png",
            headers={
                "X-Total-Spaces": str(summary.total_spaces),
                "X-Occupied-Spaces": str(summary.occupied_spaces),
                "X-Available-Spaces": str(summary.available_spaces),
                "X-Status-Changes": str(outcome.response.status_changes),
            },
        )
    return outcome.response


@router.post("/detect/video", response_model=VideoDetectionResponse)
def detect_video(
    file: UploadFile = File(..., description="Parking-lot video (mp4, avi, mov, mkv, webm)"),
    frame_interval: Optional[int] = Query(
        None,
        ge=1,
        le=100_000,
        description="Analyse every Nth frame. Default comes from the server settings.",
    ),
    max_frames: Optional[int] = Query(
        None, ge=1, description="Stop after this many analysed frames (server cap applies)."
    ),
    confirm_frames: Optional[int] = Query(
        None,
        ge=1,
        le=100,
        description="A new status must appear in this many analysed frames in a row.",
    ),
    db: Session = Depends(get_db),
):
    """Process an uploaded video frame by frame and update the availability."""
    try:
        video_path = services.save_video_upload(file)
    except services.ServiceError as exc:
        raise _http_error(exc) from exc

    try:
        response, annotated = services.process_video(
            db,
            video_path,
            frame_interval=frame_interval,
            max_frames=max_frames,
            confirm_frames=confirm_frames,
        )
    except services.ServiceError as exc:
        raise _http_error(exc) from exc
    finally:
        video_path.unlink(missing_ok=True)

    filename = services.save_processed_image(annotated)
    response.processed_image_url = f"/api/parking/processed/{filename}"
    return response


@router.post("/detect/simulate", response_model=DetectionResponse)
def detect_simulate(
    payload: Optional[SimulationRequest] = Body(None),
    db: Session = Depends(get_db),
):
    """Randomly change occupancy to test the system without a camera."""
    payload = payload or SimulationRequest()
    try:
        return services.simulate_occupancy(db, payload.occupancy_rate, payload.seed)
    except services.ServiceError as exc:
        raise _http_error(exc) from exc


_PROCESSED_NAME = re.compile(r"processed_\d{8}_\d{6}_[0-9a-f]{8}\.png")


@router.get("/processed/{filename}", response_class=FileResponse)
def get_processed_image(filename: str):
    """Download an annotated image created by a detection request."""
    path = Path(settings.processed_images_dir) / filename
    if not _PROCESSED_NAME.fullmatch(filename) or not path.is_file():
        raise HTTPException(status_code=404, detail="Processed image not found.")
    return FileResponse(path, media_type="image/png")
