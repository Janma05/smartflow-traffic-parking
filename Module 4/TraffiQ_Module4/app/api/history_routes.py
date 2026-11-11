
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.parking import ParkingLocation, ParkingOccupancy


router = APIRouter(
    prefix="/api/parking",
    tags=["Parking History"]
)


@router.get("/history/{location_id}")
def get_parking_history(
    location_id: int,
    db: Session = Depends(get_db)
):

    location = db.query(ParkingLocation).filter(
        ParkingLocation.id == location_id
    ).first()

    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Parking location not found."
        )

    records = (
        db.query(ParkingOccupancy)
        .filter(ParkingOccupancy.location_id == location_id)
        .order_by(ParkingOccupancy.recorded_at.desc())
        .all()
    )

    return {
        "location_id": location.id,
        "location": location.name,
        "total_spaces": location.total_spaces,
        "total_records": len(records),
        "history": [
            {
                "record_id": record.id,
                "recorded_at": record.recorded_at,
                "occupied_spaces": record.occupied_spaces,
                "available_spaces": record.available_spaces
            }
            for record in records
        ]
    }
