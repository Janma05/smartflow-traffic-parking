
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.parking import ParkingLocation, ParkingOccupancy


router = APIRouter(
    prefix="/api/parking",
    tags=["Parking Occupancy"]
)


class OccupancyRequest(BaseModel):
    location_id: int = Field(gt=0)
    occupied_spaces: int = Field(ge=0)


@router.post("/occupancy")
def record_occupancy(
    request: OccupancyRequest,
    db: Session = Depends(get_db)
):

    # Find the parking location
    location = db.query(ParkingLocation).filter(
        ParkingLocation.id == request.location_id
    ).first()

    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found."
        )

    # Validate occupied spaces
    if request.occupied_spaces > location.total_spaces:
        raise HTTPException(
            status_code=400,
            detail="Occupied spaces cannot exceed total parking spaces."
        )

    available_spaces = (
        location.total_spaces - request.occupied_spaces
    )

    # Create occupancy record
    record = ParkingOccupancy(
        location_id=location.id,
        occupied_spaces=request.occupied_spaces,
        available_spaces=available_spaces
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "Parking occupancy recorded successfully",
        "record_id": record.id,
        "location": location.name,
        "total_spaces": location.total_spaces,
        "occupied_spaces": record.occupied_spaces,
        "available_spaces": record.available_spaces,
        "recorded_at": record.recorded_at
    }
