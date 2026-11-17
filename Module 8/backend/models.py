
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from backend.database import Base


class TrafficObservation(Base):
    __tablename__ = "traffic_observations"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(150), nullable=False, index=True)
    observation_type = Column(String(50), nullable=False)
    vehicle_count = Column(Integer, nullable=False, default=0)
    available_parking_spaces = Column(Integer, nullable=False, default=0)
    average_speed_kmh = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.now)
