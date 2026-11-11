
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

# Load the parking dataset
df = pd.read_csv("parking_data.csv")

# Input features
X = df[["hour", "day_type"]]

# Target: number of occupied parking slots
y = df["occupied_slots"]

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42
)

# Train the machine learning model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)
model.fit(X_train, y_train)

# Evaluate the model
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)

print("Parking Demand Model Trained Successfully!")
print(f"Mean Absolute Error: {mae:.2f} slots")

# Predict demand for a selected hour
hour = 18
day_type = 0  # 0 = Weekday, 1 = Weekend

future_data = pd.DataFrame({
    "hour": [hour],
    "day_type": [day_type]
})

predicted_occupied = round(model.predict(future_data)[0])
total_slots = 100
available_slots = max(0, total_slots - predicted_occupied)

print(f"\nPrediction for hour: {hour}:00")
print(f"Predicted occupied slots: {predicted_occupied}")
print(f"Estimated available slots: {available_slots}")
