"""Module 8: Historical Data and Analytics API for SmartFlow."""
import csv
import io
import math
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models import TrafficObservation
from machine_learning_forecasting.accuracy import evaluate_predictions

app = FastAPI(
    title="SmartFlow Historical Data and Analytics API",
    description="Store traffic/parking observations, analyze peak hours and busy locations, "
                "evaluate prediction accuracy, and export reports.",
    version="1.2.0",
)


@app.on_event("startup")
def initialize_database():
    Base.metadata.create_all(bind=engine)


class ObservationRequest(BaseModel):
    location: str = Field(min_length=1, max_length=150)
    observation_type: str = Field(min_length=1, max_length=50)
    vehicle_count: int = Field(default=0, ge=0)
    available_parking_spaces: int = Field(default=0, ge=0)
    average_speed_kmh: float | None = Field(default=None, ge=0)
    recorded_at: datetime | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.average_speed_kmh is not None and not math.isfinite(self.average_speed_kmh):
            raise ValueError("Average speed must be a finite number")
        self.location = self.location.strip()
        self.observation_type = self.observation_type.strip()
        if not self.location or not self.observation_type:
            raise ValueError("Location and observation type cannot be blank")
        return self


class PredictionAccuracyRequest(BaseModel):
    actual_values: list[float] = Field(min_length=1)
    predicted_values: list[float] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_values(self):
        if len(self.actual_values) != len(self.predicted_values):
            raise ValueError("Actual and predicted lists must have the same length")
        for value in self.actual_values + self.predicted_values:
            if not math.isfinite(value):
                raise ValueError("Values must be finite numbers")
            if value < 0:
                raise ValueError("Traffic counts cannot be negative")
        return self


def observation_dict(item):
    return {
        "id": item.id,
        "location": item.location,
        "observation_type": item.observation_type,
        "vehicle_count": item.vehicle_count,
        "available_parking_spaces": item.available_parking_spaces,
        "average_speed_kmh": item.average_speed_kmh,
        "recorded_at": item.recorded_at.isoformat() if item.recorded_at else None,
    }


@app.get("/")
def home():
    return {"message": "SmartFlow Historical Data and Analytics API is running", "module": 8}


@app.get("/health/db")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database connection failed; check DATABASE_URL.") from exc


@app.post("/observations", status_code=201)
def create_observation(request: ObservationRequest, db: Session = Depends(get_db)):
    item = TrafficObservation(
        location=request.location,
        observation_type=request.observation_type,
        vehicle_count=request.vehicle_count,
        available_parking_spaces=request.available_parking_spaces,
        average_speed_kmh=request.average_speed_kmh,
        recorded_at=request.recorded_at or datetime.now(),
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"message": "Observation saved", **observation_dict(item)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save observation") from exc


@app.get("/observations")
def list_observations(
    limit: int = Query(100, ge=1, le=500),
    location: str | None = Query(None, min_length=1, max_length=150),
    observation_type: str | None = Query(None, min_length=1, max_length=50),
    db: Session = Depends(get_db),
):
    query = db.query(TrafficObservation)
    if location:
        query = query.filter(TrafficObservation.location == location.strip())
    if observation_type:
        query = query.filter(TrafficObservation.observation_type == observation_type.strip())
    return [observation_dict(item) for item in
            query.order_by(TrafficObservation.recorded_at.desc()).limit(limit).all()]


@app.get("/analytics/peak-hours")
def peak_hours(db: Session = Depends(get_db)):
    rows = db.query(TrafficObservation).all()
    hourly = {}
    for row in rows:
        if row.recorded_at:
            hourly.setdefault(row.recorded_at.hour, []).append(row.vehicle_count)
    return [
        {"hour": hour, "average_vehicle_count": round(sum(counts) / len(counts), 2), "samples": len(counts)}
        for hour, counts in sorted(hourly.items(), key=lambda pair: sum(pair[1]) / len(pair[1]), reverse=True)
    ]


@app.get("/analytics/peak-vs-off-peak")
def peak_vs_off_peak(
    peak_start: int = Query(7, ge=0, le=23),
    peak_end: int = Query(10, ge=0, le=23),
    db: Session = Depends(get_db),
):
    """Compare mean vehicle counts for [peak_start, peak_end) versus remaining hours."""
    if peak_start == peak_end:
        raise HTTPException(status_code=400, detail="Peak start and end hours must differ")
    rows = db.query(TrafficObservation).all()
    peak, off_peak = [], []
    for row in rows:
        if row.recorded_at:
            hour = row.recorded_at.hour
            in_peak = (peak_start <= hour < peak_end) if peak_start < peak_end else (hour >= peak_start or hour < peak_end)
            (peak if in_peak else off_peak).append(row.vehicle_count)

    def summary(values):
        return {"samples": len(values), "average_vehicle_count": round(sum(values) / len(values), 2) if values else None}

    return {"peak_hours": {"start": peak_start, "end_exclusive": peak_end, **summary(peak)},
            "off_peak_hours": summary(off_peak)}


@app.get("/analytics/busy-locations")
def busy_locations(db: Session = Depends(get_db)):
    rows = db.query(TrafficObservation).all()
    grouped = {}
    for row in rows:
        stats = grouped.setdefault(row.location, {"counts": [], "parking": []})
        stats["counts"].append(row.vehicle_count)
        stats["parking"].append(row.available_parking_spaces)
    return [
        {"location": location,
         "average_vehicle_count": round(sum(stats["counts"]) / len(stats["counts"]), 2),
         "minimum_available_spaces": min(stats["parking"]),
         "observations": len(stats["counts"])}
        for location, stats in sorted(grouped.items(),
            key=lambda pair: sum(pair[1]["counts"]) / len(pair[1]["counts"]), reverse=True)
    ]


@app.post("/analytics/prediction-accuracy")
def prediction_accuracy(request: PredictionAccuracyRequest):
    try:
        return evaluate_predictions(request.actual_values, request.predicted_values)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/reports/export")
def export_observations_csv(db: Session = Depends(get_db)):
    records = db.query(TrafficObservation).order_by(TrafficObservation.recorded_at.desc()).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["ID", "Location", "Observation Type", "Vehicle Count",
                     "Available Parking Spaces", "Average Speed (km/h)", "Recorded At"])
    for item in records:
        writer.writerow([item.id, item.location, item.observation_type, item.vehicle_count,
                         item.available_parking_spaces, item.average_speed_kmh,
                         item.recorded_at.isoformat() if item.recorded_at else ""])
    filename = f"smartflow_observations_{datetime.now():%Y%m%d_%H%M%S}.csv"
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
