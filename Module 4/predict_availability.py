
import joblib
import pandas as pd

# Load trained ML model
model = joblib.load("models/parking_model.pkl")

# Parking location details
parking_locations = {
    "Mall": {"code": 0, "total_slots": 100},
    "Office": {"code": 1, "total_slots": 80},
    "Hospital": {"code": 2, "total_slots": 60}
}

# Day conversion
days = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

print("SMARTFLOW - PARKING AVAILABILITY PREDICTION")
print("--------------------------------------------")

# Select parking location
print("\nAvailable Locations:")
for location in parking_locations:
    print("-", location)

location = input("\nEnter parking location: ").strip().title()

if location not in parking_locations:
    print("Invalid parking location!")
    raise SystemExit

# Select day
day = input("Enter day: ").strip().title()

if day not in days:
    print("Invalid day!")
    raise SystemExit

# Select hour
try:
    hour = int(input("Enter hour (0-23): "))

    if not 0 <= hour <= 23:
        print("Please enter an hour between 0 and 23.")
        raise SystemExit

except ValueError:
    print("Please enter a valid number!")
    raise SystemExit

# Prepare input data
input_data = pd.DataFrame([{
    "location": parking_locations[location]["code"],
    "day": days[day],
    "hour": hour
}])

# Predict occupied parking slots
predicted_occupied = model.predict(input_data)[0]

total_slots = parking_locations[location]["total_slots"]

# Calculate available parking slots
occupied_slots = max(
    0, min(total_slots, round(predicted_occupied))
)

available_slots = total_slots - occupied_slots

# Display prediction
print("\nPARKING PREDICTION RESULT")
print("------------------------")
print("Location:", location)
print("Day:", day)
print("Time:", f"{hour:02d}:00")
print("Total Parking Slots:", total_slots)
print("Predicted Occupied Slots:", occupied_slots)
print("Predicted Available Slots:", available_slots)

print("\nPrediction Completed Successfully!")
