"""Pydantic schemas used to validate API requests and shape API responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SpaceStatus = Literal["occupied", "vacant"]

MAX_COORDINATE = 100_000  # sanity limit, far larger than any real camera image


# --------------------------------------------------------------------------- #
# Parking spaces
# --------------------------------------------------------------------------- #
class ParkingSpaceCreate(BaseModel):
    """Body for ``POST /api/parking/spaces``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100, examples=["Parking Space 1"])
    x: int = Field(..., ge=0, le=MAX_COORDINATE, description="Left edge in pixels")
    y: int = Field(..., ge=0, le=MAX_COORDINATE, description="Top edge in pixels")
    width: int = Field(..., gt=0, le=MAX_COORDINATE, description="Width in pixels")
    height: int = Field(..., gt=0, le=MAX_COORDINATE, description="Height in pixels")


class ParkingSpaceUpdate(BaseModel):
    """Body for ``PUT /api/parking/spaces/{space_id}``. Send only what changes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    x: Optional[int] = Field(None, ge=0, le=MAX_COORDINATE)
    y: Optional[int] = Field(None, ge=0, le=MAX_COORDINATE)
    width: Optional[int] = Field(None, gt=0, le=MAX_COORDINATE)
    height: Optional[int] = Field(None, gt=0, le=MAX_COORDINATE)
    status: Optional[SpaceStatus] = Field(
        None, description='Manual override: "occupied" or "vacant"'
    )

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ParkingSpaceUpdate":
        provided = {k for k in self.model_fields_set if getattr(self, k) is not None}
        if not provided:
            raise ValueError("Provide at least one field to update.")
        return self


class ParkingSpaceResponse(BaseModel):
    """A parking space as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    x: int
    y: int
    width: int
    height: int
    status: SpaceStatus
    last_updated: datetime


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
class ParkingSummary(BaseModel):
    total_spaces: int
    occupied_spaces: int
    available_spaces: int
    occupancy_percentage: float
    availability_percentage: float


# --------------------------------------------------------------------------- #
# Detection / simulation
# --------------------------------------------------------------------------- #
class SpaceDetectionResult(BaseModel):
    space_id: int
    name: str
    status: SpaceStatus
    occupancy_score: Optional[float] = Field(
        None,
        description="Detector score for this parking space (None if not measured).",
    )
    changed: bool = Field(..., description="True if the saved status changed.")


class DetectionResponse(BaseModel):
    detector: str
    spaces_processed: int
    status_changes: int
    results: list[SpaceDetectionResult]
    summary: ParkingSummary
    processed_image_url: Optional[str] = None
    warnings: list[str] = []


class VideoDetectionResponse(DetectionResponse):
    frames_read: int
    frames_processed: int
    frame_interval: int
    confirm_frames: int


class SimulationRequest(BaseModel):
    """Body for ``POST /api/parking/detect/simulate``."""

    occupancy_rate: float = Field(
        0.5, ge=0.0, le=1.0, description="Fraction of spaces to mark as occupied."
    )
    seed: Optional[int] = Field(
        None, description="Set a number to get the same random result every time."
    )
