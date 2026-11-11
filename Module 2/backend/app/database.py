"""Database configuration: engine, session factory and the ``get_db`` dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# SQLite needs this flag because FastAPI may use a different thread per request.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

# pool_pre_ping reconnects automatically if PostgreSQL dropped an idle connection.
engine = create_engine(
    settings.database_url, connect_args=_connect_args, pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (runs automatically when the application starts)."""
    from app import models  # noqa: F401  (registers the models on Base)

    Base.metadata.create_all(bind=engine)
