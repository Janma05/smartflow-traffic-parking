"""Metrics for evaluating numeric traffic predictions."""
import math


def evaluate_predictions(actual_values, predicted_values):
    """Return MAE, RMSE and MAPE (%); MAPE is None if all actuals are zero."""
    if len(actual_values) != len(predicted_values):
        raise ValueError("Actual and predicted values must have the same length")
    if not actual_values:
        raise ValueError("At least one observation is required")

    values = list(actual_values) + list(predicted_values)
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("Values must be finite numbers")
    if any(value < 0 for value in values):
        raise ValueError("Traffic counts cannot be negative")

    errors = [actual - predicted for actual, predicted in zip(actual_values, predicted_values)]
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error ** 2 for error in errors) / len(errors))
    nonzero_actuals = [
        abs(error / actual) * 100
        for actual, error in zip(actual_values, errors)
        if actual != 0
    ]
    mape = sum(nonzero_actuals) / len(nonzero_actuals) if nonzero_actuals else None

    return {
        "sample_count": len(actual_values),
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape_percent": round(mape, 2) if mape is not None else None,
    }
