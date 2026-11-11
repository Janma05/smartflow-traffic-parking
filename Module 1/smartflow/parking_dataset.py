
import pandas as pd

data = {
    "hour": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
             8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    "day_type": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    "total_slots": [100] * 20,
    "occupied_slots": [30, 45, 60, 70, 80, 75, 65, 60, 70, 85,
                       20, 35, 50, 55, 65, 60, 50, 45, 55, 70]
}

df = pd.DataFrame(data)

df["available_slots"] = (
    df["total_slots"] - df["occupied_slots"]
)

df.to_csv("parking_data.csv", index=False)

print("Parking dataset created successfully!")
print(df.head(10))
print("\nDataset saved as parking_data.csv")
