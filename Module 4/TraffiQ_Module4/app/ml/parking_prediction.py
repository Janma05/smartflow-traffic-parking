
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime


# Model path
MODEL_PATH = Path("app/ml/artifacts/parking_demand_model.joblib")


def load_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Trained parking model not found. Train the model first."
        )

    saved_data = joblib.load(MODEL_PATH)

    return (
        saved_data["model"],
        saved_data["location_mapping"],
        saved_data["features"]
    )


def predict_parking(location, date, hour, total_spaces):

    # Validate input
    if not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23.")

    if total_spaces <= 0:
        raise ValueError("Total spaces must be greater than zero.")

    # Load trained model
    model, location_mapping, features = load_model()

    # Check parking location
    if location not in location_mapping:
        raise ValueError(
            f"Unknown parking location: {location}"
        )

    # Convert date
    prediction_date = pd.to_datetime(date)

    # Extract date features
    day_of_week = prediction_date.day_of_week
    is_weekend = 1 if day_of_week >= 5 else 0

    # Prepare input
    input_data = pd.DataFrame([{
        "location_code": location_mapping[location],
        "hour": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "month": prediction_date.month,
        "day": prediction_date.day,
        "total_spaces": total_spaces
    }])

    # Arrange features in training order
    input_data = input_data[features]

    # Predict occupied spaces
    predicted_occupied = float(model.predict(input_data)[0])

    # Keep prediction within parking capacity
    predicted_occupied = max(
        0,
        min(total_spaces, predicted_occupied)
    )

    predicted_occupied = round(predicted_occupied)

    # Calculate availability
    predicted_available = total_spaces - predicted_occupied

    availability_percentage = round(
        (predicted_available / total_spaces) * 100,
        2
    )

    # Determine parking status
    if availability_percentage >= 50:
        status = "High Availability"
    elif availability_percentage >= 20:
        status = "Moderate Availability"
    else:
        status = "Low Availability"

    # Return prediction
    return {
        "location": location,
        "prediction_date": str(prediction_date.date()),
        "prediction_hour": hour,
        "total_spaces": total_spaces,
        "predicted_demand": predicted_occupied,
        "predicted_occupied": predicted_occupied,
        "predicted_available": predicted_available,
        "availability_percentage": availability_percentage,
        "status": status
    }


# Test prediction
if __name__ == "__main__":

    result = predict_parking(
        location="MG Road",
        date="2026-11-10",
        hour=13,
        total_spaces=120
    )

    print("\nPARKING PREDICTION RESULT")

    for key, value in result.items():
        print(f"{key}: {value}")
