
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from math import radians, sin, cos, sqrt, atan2
from sqlalchemy.orm import Session

from app.ml.parking_prediction import predict_parking
from app.db.database import get_db
from app.models.parking import ParkingLocation


router = APIRouter(
    prefix="/api/parking",
    tags=["Parking Availability"]
)


# Request model for parking prediction
class ParkingRequest(BaseModel):
    location: str
    date: str
    hour: int = Field(ge=0, le=23)
    total_spaces: int = Field(gt=0)


# Request model for database-based recommendations
class RecommendationRequest(BaseModel):
    date: str
    hour: int = Field(ge=0, le=23)
    user_latitude: float = Field(ge=-90, le=90)
    user_longitude: float = Field(ge=-180, le=180)


# Calculate distance using Haversine formula
def calculate_distance(lat1, lon1, lat2, lon2):

    earth_radius = 6371

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(earth_radius * c, 2)


# 1. Predict future parking demand
@router.post("/predict-demand")
def predict_demand(request: ParkingRequest):

    try:
        return predict_parking(
            location=request.location,
            date=request.date,
            hour=request.hour,
            total_spaces=request.total_spaces
        )

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=400, detail=str(error))


# 2. Estimate parking availability
@router.post("/availability")
def estimate_availability(request: ParkingRequest):

    try:
        result = predict_parking(
            location=request.location,
            date=request.date,
            hour=request.hour,
            total_spaces=request.total_spaces
        )

        return {
            "location": result["location"],
            "date": result["prediction_date"],
            "hour": result["prediction_hour"],
            "total_spaces": result["total_spaces"],
            "predicted_occupied": result["predicted_occupied"],
            "predicted_available": result["predicted_available"],
            "availability_percentage": result["availability_percentage"],
            "status": result["status"]
        }

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=400, detail=str(error))


# 3. Recommend nearby parking using SQLite locations
@router.post("/recommendations")
def recommend_parking(
    request: RecommendationRequest,
    db: Session = Depends(get_db)
):

    # Fetch parking locations from SQLite
    parking_locations = db.query(ParkingLocation).all()

    if not parking_locations:
        raise HTTPException(
            status_code=404,
            detail="No parking locations found in the database."
        )

    recommendations = []

    try:
        for parking in parking_locations:

            prediction = predict_parking(
                location=parking.name,
                date=request.date,
                hour=request.hour,
                total_spaces=parking.total_spaces
            )

            distance = calculate_distance(
                request.user_latitude,
                request.user_longitude,
                parking.latitude,
                parking.longitude
            )

            # Combined score:
            # 70% expected availability + 30% distance
            availability_score = (
                prediction["availability_percentage"] / 100
            )

            distance_score = 1 / (1 + distance)

            final_score = (
                0.70 * availability_score
                + 0.30 * distance_score
            )

            recommendations.append({
                "location_id": parking.id,
                "location": parking.name,
                "distance_km": distance,
                "total_spaces": parking.total_spaces,
                "predicted_available": prediction["predicted_available"],
                "availability_percentage": prediction["availability_percentage"],
                "status": prediction["status"],
                "recommendation_score": round(final_score * 100, 2)
            })

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=400, detail=str(error))

    # Rank by combined score, then shortest distance
    recommendations.sort(
        key=lambda item: (
            -item["recommendation_score"],
            item["distance_km"]
        )
    )

    for rank, item in enumerate(recommendations, start=1):
        item["rank"] = rank

    return {
        "prediction_date": request.date,
        "prediction_hour": request.hour,
        "ranking_method": "70% availability + 30% distance",
        "total_locations": len(recommendations),
        "recommendations": recommendations
    }
