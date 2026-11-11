import joblib
import pandas as pd
from parking_config import TOTAL_PARKING_SLOTS

# Load trained model
model = joblib.load("models/video_parking_model.pkl")

print("SMARTFLOW PARKING AVAILABILITY PREDICTION")

# Get time in seconds
seconds = float(input("Enter video time in seconds: "))

# Predict occupied vehicles
input_data = pd.DataFrame({
    "elapsed_seconds": [seconds]
})

predicted_occupied = model.predict(input_data)[0]

# Calculate availability
occupied = max(
    0,
    min(TOTAL_PARKING_SLOTS, round(predicted_occupied))
)

available = TOTAL_PARKING_SLOTS - occupied

print("\nPARKING PREDICTION RESULTS")
print("Total Parking Slots:", TOTAL_PARKING_SLOTS)
print("Predicted Occupied:", occupied)
print("Predicted Available:", available)