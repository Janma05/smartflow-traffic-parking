
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.database import Base


class ParkingLocation(Base):

    __tablename__ = "parking_locations"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    total_spaces = Column(Integer, nullable=False)

    occupancy_records = relationship(
        "ParkingOccupancy",
        back_populates="location",
        cascade="all, delete-orphan"
    )


class ParkingOccupancy(Base):

    __tablename__ = "parking_occupancy"

    id = Column(Integer, primary_key=True, index=True)

    location_id = Column(
        Integer,
        ForeignKey("parking_locations.id"),
        nullable=False
    )

    recorded_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    occupied_spaces = Column(Integer, nullable=False)

    available_spaces = Column(Integer, nullable=False)

    location = relationship(
        "ParkingLocation",
        back_populates="occupancy_records"
    )
