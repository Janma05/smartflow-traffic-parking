
import pandas as pd
import joblib

from pathlib import Path
from sqlalchemy.orm import Session

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

from app.db.database import SessionLocal
from app.models.parking import ParkingLocation, ParkingOccupancy


# Project paths
PROJECT_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = PROJECT_DIR / "data" / "parking_data.csv"
MODEL_DIR = PROJECT_DIR / "app" / "ml" / "artifacts"
MODEL_PATH = MODEL_DIR / "parking_demand_model.joblib"


def load_csv_data():
    print("Loading CSV parking dataset...")

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Parking dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH)

    return df


def load_database_history():
    print("Loading SQLite occupancy history...")

    db: Session = SessionLocal()

    try:
        records = (
            db.query(ParkingOccupancy, ParkingLocation)
            .join(
                ParkingLocation,
                ParkingOccupancy.location_id == ParkingLocation.id
            )
            .all()
        )

        history = []

        for record, location in records:
            recorded_time = record.recorded_at

            history.append({
                "location": location.name,
                "date": recorded_time.date(),
                "hour": recorded_time.hour,
                "day_of_week": recorded_time.weekday(),
                "is_weekend": (
                    1 if recorded_time.weekday() >= 5 else 0
                ),
                "occupied_spaces": record.occupied_spaces,
                "total_spaces": location.total_spaces
            })

        return pd.DataFrame(history)

    finally:
        db.close()


def train_parking_model():

    # 1. Load CSV data
    csv_df = load_csv_data()

    # 2. Load database history
    history_df = load_database_history()

    # 3. Combine datasets
    if not history_df.empty:
        df = pd.concat(
            [csv_df, history_df],
            ignore_index=True
        )

        print("CSV and database history combined.")

    else:
        df = csv_df.copy()

        print("No database history found. Using CSV data only.")

    # 4. Check required columns
    required_columns = [
        "location",
        "date",
        "hour",
        "occupied_spaces",
        "total_spaces"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing dataset columns: {missing_columns}"
        )

    if df.empty:
        raise ValueError("Training dataset is empty.")

    # 5. Convert date column
    df["date"] = pd.to_datetime(
        df["date"],
        errors="raise"
    )

    # 6. Feature engineering
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day

    # Updated Pandas property (warning fixed)
    df["day_of_week"] = df["date"].dt.day_of_week

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # 7. Validate numeric data
    df["hour"] = pd.to_numeric(
        df["hour"],
        errors="raise"
    )

    df["occupied_spaces"] = pd.to_numeric(
        df["occupied_spaces"],
        errors="raise"
    )

    df["total_spaces"] = pd.to_numeric(
        df["total_spaces"],
        errors="raise"
    )

    if df["location"].isna().any():
        raise ValueError("Location names cannot be empty.")

    if not df["hour"].between(0, 23).all():
        raise ValueError("Hour must be between 0 and 23.")

    if (df["total_spaces"] <= 0).any():
        raise ValueError(
            "Total parking spaces must be positive."
        )

    if (
        (df["occupied_spaces"] < 0)
        | (df["occupied_spaces"] > df["total_spaces"])
    ).any():
        raise ValueError(
            "Invalid occupied parking spaces in dataset."
        )

    # 8. Create location mapping
    location_names = sorted(
        df["location"].unique()
    )

    location_mapping = {
        name: code
        for code, name in enumerate(location_names)
    }

    df["location_code"] = df["location"].map(
        location_mapping
    )

    # 9. Define ML features
    features = [
        "location_code",
        "hour",
        "day_of_week",
        "is_weekend",
        "month",
        "day",
        "total_spaces"
    ]

    X = df[features]
    y = df["occupied_spaces"]

    print("\n========== DATASET SUMMARY ==========")
    print("Total training records:", len(df))
    print("CSV records:", len(csv_df))
    print("Database records:", len(history_df))
    print("Parking locations:", location_names)

    # 10. Split dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    print("\nTraining Random Forest model...")

    # 11. Train model
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42
    )

    model.fit(X_train, y_train)

    # 12. Evaluate model
    predictions = model.predict(X_test)

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    print("\n========== MODEL EVALUATION ==========")
    print("Mean Absolute Error:", round(mae, 2))
    print("R2 Score:", round(r2, 2))

    # 13. Save trained model
    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        {
            "model": model,
            "location_mapping": location_mapping,
            "features": features
        },
        MODEL_PATH
    )

    print("\n========== TRAINING COMPLETED ==========")
    print("Model saved successfully!")
    print("Model path:", MODEL_PATH)


if __name__ == "__main__":
    train_parking_model()

