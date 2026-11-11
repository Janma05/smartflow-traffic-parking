"""SQLAlchemy ORM models."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

STATUS_OCCUPIED = "occupied"
STATUS_VACANT = "vacant"


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (SQLite does not store time zones)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ParkingSpace(Base):
    """One rectangular parking space inside the camera image."""

    __tablename__ = "parking_spaces"
    __table_args__ = (
        CheckConstraint("status IN ('occupied', 'vacant')", name="ck_space_status"),
        CheckConstraint("x >= 0 AND y >= 0", name="ck_space_coordinates"),
        CheckConstraint("width > 0 AND height > 0", name="ck_space_size"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default=STATUS_VACANT
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
