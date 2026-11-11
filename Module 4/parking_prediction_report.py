import pandas as pd
import joblib
from parking_config import TOTAL_PARKING_SLOTS

# Load video observations
data = pd.read_csv("dataset/parking_video_observations.csv")

# Load trained model
model = joblib.load("models/video_parking_model.pkl")

# Calculate summary
total_observations = len(data)
average_vehicles = data["vehicle_count"].mean()
average_occupied = data["estimated_occupied"].mean()
average_available = data["estimated_available"].mean()

# Generate report
report = f"""
SMARTFLOW - PARKING AVAILABILITY PREDICTION REPORT
=================================================

Total Parking Capacity: {TOTAL_PARKING_SLOTS}
Total Video Observations: {total_observations}

Average Detected Vehicles: {average_vehicles:.2f}
Average Estimated Occupied Slots: {average_occupied:.2f}
Average Estimated Available Slots: {average_available:.2f}

Model: Random Forest Regressor
Input Feature: Elapsed Video Time
Target: Estimated Occupied Slots

NOTE:
Occupancy values are estimates based on vehicle detections.
They are not verified parking-slot occupancy measurements.
"""

with open("outputs/parking_prediction_report.txt", "w") as file:
    file.write(report)

print(report)
print("Report saved successfully!")