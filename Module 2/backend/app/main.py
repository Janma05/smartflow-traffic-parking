"""Application entry point.  Run with:  uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.routers import parking

DESCRIPTION = """
Detects **occupied** and **vacant** parking spaces in images and videos with
OpenCV, stores the latest status of every space in SQLite and calculates the
parking availability.

**How detection works:** each space is a rectangle you configure in pixel
coordinates. The detector measures how many edges (Canny) are inside the
rectangle; many edges = a vehicle, few edges = empty ground.

**Limitations:** this is a basic method that has not been validated on real
footage. Lighting, shadows, surface texture, camera angle and weather can
cause wrong results, and the threshold needs calibrating per camera. Use
`POST /api/parking/detect/simulate` to test without a camera.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at start-up: create folders and the SQLite tables.
    settings.ensure_dirs()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRIPTION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(parking.router)


@app.get("/", tags=["General"])
def root():
    """Welcome message."""
    return {
        "message": f"Welcome to the {settings.app_name} API",
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health", tags=["General"])
def health(db: Session = Depends(get_db)):
    """Check that the backend and its database are running."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # database unreachable
        raise HTTPException(status_code=503, detail="Database is not reachable.") from exc
    return {"status": "ok", "database": "connected"}
