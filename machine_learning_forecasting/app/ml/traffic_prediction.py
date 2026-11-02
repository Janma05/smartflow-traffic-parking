from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    accuracy_score,
    classification_report,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression


# --------------------------------------------------
# PATH CONFIGURATION
# --------------------------------------------------

MODEL_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

REGRESSION_PATH = MODEL_DIR / "traffic_volume_model.joblib"
CLASSIFICATION_PATH = MODEL_DIR / "congestion_model.joblib"

REQUIRED = {"timestamp", "vehicle_count"}

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "month",
    "lag_1",
    "lag_2",
    "rolling_mean_3",
    "rolling_mean_6",
]


# --------------------------------------------------
# LOAD AND CLEAN TRAFFIC DATA
# --------------------------------------------------

def load_data(csv_path: str) -> pd.DataFrame:
    """
    Load traffic history from CSV and clean the data.

    Supports different timestamp formats, including:
    2026-09-01 00:00:00
    2026-11-02T10:10:49
    """

    csv_file = Path(csv_path)

    if not csv_file.exists():
        raise FileNotFoundError(
            f"Traffic history CSV not found: {csv_file.resolve()}"
        )

    df = pd.read_csv(csv_file)

    missing = REQUIRED - set(df.columns)

    if missing:
        raise ValueError(
            f"CSV is missing required columns: {sorted(missing)}"
        )

    original_rows = len(df)

    # Support mixed timestamp formats.
    # format='mixed' is supported by pandas 2.0 and newer.
    try:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
            format="mixed",
        )
    except (TypeError, ValueError):
        # Compatibility fallback for older pandas versions.
        df["timestamp"] = pd.to_datetime(
            df["timestamp"],
            errors="coerce",
        )

    # Convert vehicle counts into numeric values.
    df["vehicle_count"] = pd.to_numeric(
        df["vehicle_count"],
        errors="coerce",
    )

    # Remove rows only when essential fields are invalid.
    df = df.dropna(
        subset=["timestamp", "vehicle_count"]
    ).copy()

    # Vehicle counts cannot be negative.
    df = df[df["vehicle_count"] >= 0].copy()

    # Preserve location information.
    if "location_id" not in df.columns:
        df["location_id"] = "default"

    df["location_id"] = (
        df["location_id"]
        .fillna("default")
        .astype(str)
        .str.strip()
    )

    df.loc[
        df["location_id"] == "",
        "location_id"
    ] = "default"

    # Clean optional average-speed values.
    if "average_speed" in df.columns:
        df["average_speed"] = pd.to_numeric(
            df["average_speed"],
            errors="coerce",
        )

    dropped_rows = original_rows - len(df)

    print("\n========== TRAFFIC DATA LOADING ==========")
    print(f"CSV file: {csv_file.resolve()}")
    print(f"Original CSV data rows: {original_rows}")
    print(f"Valid records loaded: {len(df)}")
    print(f"Rows removed during cleaning: {dropped_rows}")
    print("\nRecords by location:")

    print(
        df["location_id"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("==========================================\n")

    return (
        df.sort_values(["location_id", "timestamp"])
        .reset_index(drop=True)
    )


# --------------------------------------------------
# CONGESTION CLASSIFICATION
# --------------------------------------------------

def congestion_from_thresholds(
    counts: pd.Series,
    low: float,
    high: float,
) -> pd.Series:

    return pd.Series(
        np.where(
            counts <= low,
            "Low",
            np.where(counts <= high, "Medium", "High"),
        ),
        index=counts.index,
    )


# --------------------------------------------------
# FEATURE ENGINEERING
# --------------------------------------------------

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create time-based and historical features for prediction.
    Historical features are calculated separately per location.
    """

    out = df.sort_values(
        ["location_id", "timestamp"]
    ).copy()

    timestamp = out["timestamp"]

    out["hour"] = timestamp.dt.hour
    out["day_of_week"] = timestamp.dt.dayofweek
    out["is_weekend"] = (
        timestamp.dt.dayofweek >= 5
    ).astype(int)
    out["month"] = timestamp.dt.month

    grouped_counts = out.groupby(
        "location_id",
        sort=False,
    )["vehicle_count"]

    out["lag_1"] = grouped_counts.shift(1)
    out["lag_2"] = grouped_counts.shift(2)

    out["rolling_mean_3"] = grouped_counts.transform(
        lambda series: (
            series.shift(1)
            .rolling(3, min_periods=1)
            .mean()
        )
    )

    out["rolling_mean_6"] = grouped_counts.transform(
        lambda series: (
            series.shift(1)
            .rolling(6, min_periods=1)
            .mean()
        )
    )

    return out


# --------------------------------------------------
# HISTORICAL TRAFFIC ANALYSIS
# --------------------------------------------------

def analyze_history(csv_path: str) -> dict:
    """
    Analyze historical traffic records across all locations.
    """

    df = load_data(csv_path)

    if df.empty:
        raise ValueError(
            "No valid traffic records are available for analysis."
        )

    df["hour"] = df["timestamp"].dt.hour
    df["day_name"] = df["timestamp"].dt.day_name()

    # Calculate dataset-based congestion thresholds.
    low, high = df["vehicle_count"].quantile(
        [0.33, 0.67]
    ).tolist()

    # Hourly statistics.
    hourly = (
        df.groupby("hour")["vehicle_count"]
        .agg(["mean", "max", "count"])
        .reset_index()
    )

    # Busy periods by day and hour.
    day_hour = (
        df.groupby(
            ["day_name", "hour"],
            as_index=False,
        )["vehicle_count"]
        .mean()
    )

    busy = (
        day_hour.sort_values(
            "vehicle_count",
            ascending=False,
        )
        .head(10)
    )

    congestion = congestion_from_thresholds(
        df["vehicle_count"],
        low,
        high,
    )

    busiest_hour = int(
        hourly.loc[
            hourly["mean"].idxmax(),
            "hour",
        ]
    )

    return {
        "records_analyzed": int(len(df)),

        "locations": sorted(
            df["location_id"].unique().tolist()
        ),

        "records_by_location": {
            str(location): int(count)
            for location, count
            in df["location_id"].value_counts().items()
        },

        "date_range": {
            "start": df["timestamp"].min().isoformat(),
            "end": df["timestamp"].max().isoformat(),
        },

        "average_vehicle_count": round(
            float(df["vehicle_count"].mean()),
            2,
        ),

        "maximum_vehicle_count": int(
            df["vehicle_count"].max()
        ),

        "busiest_average_hour": busiest_hour,

        "hourly_summary": [
            {
                "hour": int(row["hour"]),
                "average_vehicle_count": round(
                    float(row["mean"]), 2
                ),
                "max_vehicle_count": int(
                    row["max"]
                ),
                "records": int(
                    row["count"]
                ),
            }
            for _, row in hourly.iterrows()
        ],

        "recurring_busy_periods": [
            {
                "day": str(row.day_name),
                "hour": int(row.hour),
                "average_vehicle_count": round(
                    float(row.vehicle_count), 2
                ),
            }
            for row in busy.itertuples(index=False)
        ],

        "congestion_distribution": {
            str(label): int(count)
            for label, count
            in congestion.value_counts().items()
        },

        "thresholds_from_dataset": {
            "low_max": round(float(low), 2),
            "medium_max": round(float(high), 2),
        },
    }


# --------------------------------------------------
# PREPARE TRAINING DATA
# --------------------------------------------------

def prepare_training_data(
    csv_path: str,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:

    df = load_data(csv_path)

    if df.empty:
        raise ValueError(
            "No valid traffic records are available for training."
        )

    featured = add_features(df)

    # Fill missing lag values for the beginning of each location's history.
    featured["lag_1"] = (
        featured.groupby("location_id")["vehicle_count"]
        .transform(
            lambda series: series.shift(1)
        )
    )

    for column in [
        "lag_1",
        "lag_2",
        "rolling_mean_3",
        "rolling_mean_6",
    ]:
        featured[column] = (
            featured.groupby("location_id")[column]
            .transform(lambda series: series.bfill())
        )

        featured[column] = featured[column].fillna(
            featured["vehicle_count"].median()
        )

    X = featured[FEATURES].copy()
    y = featured["vehicle_count"].copy()

    return X, y, featured


# --------------------------------------------------
# TRAIN TRAFFIC VOLUME MODEL
# --------------------------------------------------

def train_traffic_model(csv_path: str) -> dict:
    """
    Train a Random Forest regression model and save it.
    """

    X, y, featured = prepare_training_data(csv_path)

    if len(X) < 2:
        raise ValueError(
            "At least two valid observations are required for training."
        )

    # Use chronological ordering to avoid training on future records
    # and testing on earlier records.
    split_index = int(len(X) * 0.8)

    split_index = min(
        max(split_index, 1),
        len(X) - 1,
    )

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = float(
        np.sqrt(
            mean_squared_error(
                y_test,
                predictions,
            )
        )
    )

    joblib.dump(
        {
            "model": model,
            "features": FEATURES,
        },
        REGRESSION_PATH,
    )

    return {
        "status": "success",
        "model": "RandomForestRegressor",
        "records_used": int(len(X)),
        "training_records": int(len(X_train)),
        "testing_records": int(len(X_test)),
        "mae": round(float(mae), 4),
        "rmse": round(rmse, 4),
        "model_path": str(REGRESSION_PATH),
    }


# --------------------------------------------------
# TRAIN CONGESTION CLASSIFICATION MODEL
# --------------------------------------------------

def train_congestion_model(csv_path: str) -> dict:
    """
    Train a Random Forest classifier for Low, Medium, and High congestion.
    """

    X, y, featured = prepare_training_data(csv_path)

    if len(X) < 2:
        raise ValueError(
            "At least two valid observations are required for training."
        )

    low, high = y.quantile([0.33, 0.67]).tolist()

    labels = congestion_from_thresholds(
        y,
        low,
        high,
    )

    split_index = int(len(X) * 0.8)

    split_index = min(
        max(split_index, 1),
        len(X) - 1,
    )

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = labels.iloc[:split_index]
    y_test = labels.iloc[split_index:]

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    report = classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    )

    joblib.dump(
        {
            "model": model,
            "features": FEATURES,
            "low_threshold": float(low),
            "high_threshold": float(high),
        },
        CLASSIFICATION_PATH,
    )

    return {
        "status": "success",
        "model": "RandomForestClassifier",
        "records_used": int(len(X)),
        "training_records": int(len(X_train)),
        "testing_records": int(len(X_test)),
        "accuracy": round(float(accuracy), 4),
        "classification_report": report,
        "thresholds": {
            "low_max": round(float(low), 2),
            "medium_max": round(float(high), 2),
        },
        "model_path": str(CLASSIFICATION_PATH),
    }


# --------------------------------------------------
# PREDICT TRAFFIC VOLUME
# --------------------------------------------------

def predict_traffic(
    timestamp: str,
    location_id: str,
    csv_path: str,
) -> dict:
    """
    Predict traffic volume for a specified location and timestamp.
    """

    if not REGRESSION_PATH.exists():
        raise FileNotFoundError(
            "Traffic model is not trained. "
            "Run /prediction/train first."
        )

    saved = joblib.load(REGRESSION_PATH)

    model = saved["model"]

    feature_columns = saved.get(
        "features",
        FEATURES,
    )

    df = load_data(csv_path)

    location_data = df[
        df["location_id"] == location_id
    ].copy()

    if location_data.empty:
        raise ValueError(
            f"No historical data found for location '{location_id}'."
        )

    target_timestamp = pd.to_datetime(
        timestamp,
        errors="raise",
    )

    location_data = location_data.sort_values(
        "timestamp"
    )

    previous_counts = location_data[
        location_data["timestamp"] < target_timestamp
    ]["vehicle_count"]

    recent = previous_counts.tail(6)

    lag_1 = (
        float(recent.iloc[-1])
        if len(recent) >= 1
        else float(location_data["vehicle_count"].median())
    )

    lag_2 = (
        float(recent.iloc[-2])
        if len(recent) >= 2
        else lag_1
    )

    rolling_mean_3 = (
        float(recent.tail(3).mean())
        if len(recent) >= 1
        else lag_1
    )

    rolling_mean_6 = (
        float(recent.mean())
        if len(recent) >= 1
        else lag_1
    )

    feature_row = pd.DataFrame(
        [
            {
                "hour": target_timestamp.hour,
                "day_of_week": target_timestamp.dayofweek,
                "is_weekend": int(
                    target_timestamp.dayofweek >= 5
                ),
                "month": target_timestamp.month,
                "lag_1": lag_1,
                "lag_2": lag_2,
                "rolling_mean_3": rolling_mean_3,
                "rolling_mean_6": rolling_mean_6,
            }
        ]
    )

    prediction = float(
        model.predict(
            feature_row[feature_columns]
        )[0]
    )

    return {
        "location_id": location_id,
        "timestamp": target_timestamp.isoformat(),
        "predicted_vehicle_count": round(
            max(0.0, prediction),
            2,
        ),
        "model": "RandomForestRegressor",
    }
def train_model(csv_path: str) -> dict:
    """Train the traffic volume and congestion models."""
    regression_result = train_traffic_model(csv_path)
    classification_result = train_congestion_model(csv_path)

    return {
        "status": "success",
        "regression": regression_result,
        "classification": classification_result,
    }


def predict_next(
    csv_path: str,
    location_id: str = "default",
    prediction_time: str | None = None,
) -> dict:
    """Predict traffic volume for a location and time."""

    if not REGRESSION_PATH.exists():
        raise FileNotFoundError(
            "Traffic model is not trained. Run /prediction/train first."
        )

    df = load_data(csv_path)

    location_data = df[
        df["location_id"] == location_id
    ].sort_values("timestamp")

    if location_data.empty:
        raise ValueError(
            f"No historical data found for location '{location_id}'."
        )

    if prediction_time:
        target_timestamp = pd.to_datetime(
            prediction_time,
            errors="raise",
        )
    else:
        target_timestamp = (
            location_data["timestamp"].max()
            + pd.Timedelta(hours=1)
        )

    return predict_traffic(
        timestamp=target_timestamp.isoformat(),
        location_id=location_id,
        csv_path=csv_path,
    )
