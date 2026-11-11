from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.parking import ParkingLocation

router = APIRouter(
    prefix="/api/parking",
    tags=["Parking Locations"]
)


@router.get("/locations")
def get_parking_locations(db: Session = Depends(get_db)):
    locations = db.query(ParkingLocation).all()

    return [
        {
            "id": location.id,
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "total_spaces": location.total_spaces
        }
        for location in locations
    ]