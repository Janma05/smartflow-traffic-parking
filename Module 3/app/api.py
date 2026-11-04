from pathlib import Path

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.ml.traffic_prediction import (
    analyze_history,
    train_model,
    predict_next,
    load_data,
    add_features,
    FEATURES,
    CLASSIFICATION_PATH,
)
from app.ai.vehicle_observations import append_observation


app = FastAPI(
    title="SmartFlow Module 3: Traffic Prediction",
    version="1.0.0",
    description=(
        "Traffic history analysis, ML training, "
        "traffic volume prediction, and congestion classification."
    ),
)

DEFAULT_CSV = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "traffic_history.csv"
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class CsvRequest(BaseModel):
    csv_path: str | None = None


class PredictionRequest(BaseModel):
    csv_path: str | None = None
    location_id: str = "default"
    prediction_time: str | None = None


class CongestionRequest(BaseModel):
    csv_path: str | None = None
    location_id: str = "default"
    prediction_time: str | None = None


class ObservationRequest(BaseModel):
    timestamp: str
    location_id: str = "default"
    vehicle_count: int = Field(ge=0)
    average_speed: float | None = Field(default=None, ge=0)
    csv_path: str | None = None


# --------------------------------------------------
# Resolve CSV path
# --------------------------------------------------

def resolve_csv(path: str | None = None) -> str:
    if path is None or str(path).strip().lower() in (
        "",
        "null",
        "none",
    ):
        target = DEFAULT_CSV
    else:
        target = Path(path).expanduser()

    if not target.exists():
        raise HTTPException(
            status_code=404,
            detail=f"CSV file not found: {target}",
        )

    if not target.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"The specified CSV path is not a file: {target}",
        )

    return str(target.resolve())


# --------------------------------------------------
# Root and health
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "module": "Module 3: AI/ML Traffic Prediction",
        "status": "running",
        "docs": "/docs",
        "csv_path": str(DEFAULT_CSV),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "Module 3",
        "csv_exists": DEFAULT_CSV.exists(),
        "csv_path": str(DEFAULT_CSV),
    }


# --------------------------------------------------
# Save traffic observation
# --------------------------------------------------

@app.post("/prediction/observations")
def save_observation(req: ObservationRequest):
    try:
        target = resolve_csv(req.csv_path)

        return append_observation(
            target,
            req.timestamp,
            req.location_id,
            req.vehicle_count,
            req.average_speed,
        )

    except HTTPException:
        raise
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Analyze historical traffic
# --------------------------------------------------

@app.get("/prediction/analyze")
def analyze(csv_path: str | None = Query(default=None)):
    try:
        return analyze_history(resolve_csv(csv_path))

    except HTTPException:
        raise
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Train models
# --------------------------------------------------

@app.post("/prediction/train")
def train(req: CsvRequest):
    try:
        target = resolve_csv(req.csv_path)
        result = train_model(target)

        return {
            "status": "success",
            "message": "Traffic prediction models trained successfully.",
            "csv_path": target,
            "results": result,
        }

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Predict traffic volume
# --------------------------------------------------

@app.post("/prediction/predict")
def predict(req: PredictionRequest):
    try:
        target = resolve_csv(req.csv_path)

        return predict_next(
            csv_path=target,
            location_id=req.location_id,
            prediction_time=req.prediction_time,
        )

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# --------------------------------------------------
# Predict congestion level
# --------------------------------------------------

@app.post("/prediction/congestion")
def predict_congestion(req: CongestionRequest):
    try:
        target = resolve_csv(req.csv_path)

        if not CLASSIFICATION_PATH.exists():
            raise HTTPException(
                status_code=409,
                detail=(
                    "Congestion model not trained. "
                    "Run POST /prediction/train first."
                ),
            )

        # Load historical data for the requested location.
        df = load_data(target)

        location_data = df[
            df["location_id"] == req.location_id
        ].copy()

        if location_data.empty:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No historical data found for location "
                    f"'{req.location_id}'."
                ),
            )

        # Select prediction timestamp.
        if req.prediction_time:
            target_timestamp = pd.to_datetime(
                req.prediction_time,
                errors="raise",
            )
        else:
            target_timestamp = (
                location_data["timestamp"].max()
                + pd.Timedelta(hours=1)
            )

        # Use only observations before the requested time.
        previous = location_data[
            location_data["timestamp"] < target_timestamp
        ].sort_values("timestamp")

        if previous.empty:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No historical observations exist before "
                    "the requested prediction time."
                ),
            )

        recent = previous["vehicle_count"].tail(6)

        lag_1 = float(recent.iloc[-1])
        lag_2 = (
            float(recent.iloc[-2])
            if len(recent) >= 2
            else lag_1
        )

        rolling_mean_3 = float(recent.tail(3).mean())
        rolling_mean_6 = float(recent.mean())

        feature_row = pd.DataFrame([{
            "hour": target_timestamp.hour,
            "day_of_week": target_timestamp.dayofweek,
            "is_weekend": int(target_timestamp.dayofweek >= 5),
            "month": target_timestamp.month,
            "lag_1": lag_1,
            "lag_2": lag_2,
            "rolling_mean_3": rolling_mean_3,
            "rolling_mean_6": rolling_mean_6,
        }])

        # Load the trained classifier.
        saved = joblib.load(CLASSIFICATION_PATH)
        model = saved["model"]
        feature_columns = saved.get("features", FEATURES)

        congestion = str(
            model.predict(feature_row[feature_columns])[0]
        )

        return {
            "status": "success",
            "location_id": req.location_id,
            "timestamp": target_timestamp.isoformat(),
            "predicted_congestion": congestion,
            "model": "RandomForestClassifier",
            "thresholds": {
                "low_max": saved.get("low_threshold"),
                "medium_max": saved.get("high_threshold"),
            },
        }

    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
