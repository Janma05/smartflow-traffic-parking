"""Database operations (Create, Read, Update, Delete) for parking spaces."""

from collections.abc import Mapping
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import STATUS_OCCUPIED, STATUS_VACANT, ParkingSpace, utcnow
from app.schemas import ParkingSpaceCreate, ParkingSpaceUpdate


def get_spaces(db: Session) -> list[ParkingSpace]:
    return list(db.scalars(select(ParkingSpace).order_by(ParkingSpace.id)))


def get_space(db: Session, space_id: int) -> Optional[ParkingSpace]:
    return db.get(ParkingSpace, space_id)


def create_space(db: Session, data: ParkingSpaceCreate) -> ParkingSpace:
    space = ParkingSpace(
        **data.model_dump(), status=STATUS_VACANT, last_updated=utcnow()
    )
    db.add(space)
    db.commit()
    db.refresh(space)
    return space


def update_space(
    db: Session, space: ParkingSpace, data: ParkingSpaceUpdate
) -> ParkingSpace:
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in changes.items():
        setattr(space, field, value)
    space.last_updated = utcnow()
    db.commit()
    db.refresh(space)
    return space


def delete_space(db: Session, space: ParkingSpace) -> None:
    db.delete(space)
    db.commit()


def count_spaces(db: Session) -> tuple[int, int]:
    """Return ``(total_spaces, occupied_spaces)`` straight from the database."""
    total = db.scalar(select(func.count(ParkingSpace.id))) or 0
    occupied = (
        db.scalar(
            select(func.count(ParkingSpace.id)).where(
                ParkingSpace.status == STATUS_OCCUPIED
            )
        )
        or 0
    )
    return total, occupied


def apply_statuses(db: Session, new_statuses: Mapping[int, str]) -> list[int]:
    """Save new statuses, writing ONLY the spaces whose status really changed.

    Returns the ids that changed. If nothing changed, the database is not
    written to at all (no UPDATE, no commit), and ``last_updated`` stays as is.
    """
    if not new_statuses:
        return []
    spaces = db.scalars(
        select(ParkingSpace).where(ParkingSpace.id.in_(list(new_statuses)))
    )
    changed_ids: list[int] = []
    now = utcnow()
    for space in spaces:
        new_status = new_statuses[space.id]
        if space.status != new_status:
            space.status = new_status
            space.last_updated = now
            changed_ids.append(space.id)
    if changed_ids:
        db.commit()
    return changed_ids
