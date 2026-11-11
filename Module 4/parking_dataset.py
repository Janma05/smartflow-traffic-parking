
import pandas as pd
import os

# Create parking dataset
data = {
    "location": [
        "Mall", "Mall", "Mall", "Mall",
        "Office", "Office", "Office", "Office",
        "Hospital", "Hospital", "Hospital", "Hospital"
    ],
    "day": [
        "Monday", "Monday", "Tuesday", "Tuesday",
        "Monday", "Monday", "Tuesday", "Tuesday",
        "Monday", "Monday", "Tuesday", "Tuesday"
    ],
    "hour": [
        9, 18, 9, 18,
        9, 18, 9, 18,
        9, 18, 9, 18
    ],
    "total_slots": [
        100, 100, 100, 100,
        80, 80, 80, 80,
        60, 60, 60, 60
    ],
    "occupied_slots": [
        35, 90, 40, 95,
        70, 45, 75, 50,
        50, 35, 55, 40
    ]
}

df = pd.DataFrame(data)

# Calculate available parking slots
df["available_slots"] = (
    df["total_slots"] - df["occupied_slots"]
)

# Save dataset
os.makedirs("dataset", exist_ok=True)

df.to_csv("dataset/parking_data.csv", index=False)

print("Parking dataset created successfully!")
print(df)
