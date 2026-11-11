
from fastapi import FastAPI

from app.api.parking_routes import router as parking_router
from app.api.location_routes import router as location_router
from app.api.occupancy_routes import router as occupancy_router
from app.api.history_routes import router as history_router

from app.db.database import Base, engine

# Import models so SQLAlchemy registers database tables
from app.models.parking import ParkingLocation, ParkingOccupancy


app = FastAPI(
    title="TraffiQ - Module 4 Parking Availability Prediction",
    description=(
        "Backend APIs for parking demand prediction, "
        "availability estimation, parking recommendations "
        "and occupancy history management."
    ),
    version="1.0.0"
)


# Initialize database tables
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Welcome to TraffiQ Module 4 Backend",
        "module": "Parking Availability Prediction"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "Module 4"
    }


# Register all API routers
app.include_router(parking_router)
app.include_router(location_router)
app.include_router(occupancy_router)
app.include_router(history_router)
