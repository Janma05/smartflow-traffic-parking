
import pandas as pd
import joblib
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split

# Load dataset
df = pd.read_csv("dataset/processed_parking_data.csv")

# Prepare input and output
X = df[["location", "day", "hour"]]
y = df["occupied_slots"]

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Load trained model
model = joblib.load("models/parking_model.pkl")

# Predict parking occupancy
predictions = model.predict(X_test)

# Create visualization
plt.figure(figsize=(10, 5))

plt.plot(
    range(len(y_test)),
    y_test.values,
    marker="o",
    label="Actual Occupancy"
)

plt.plot(
    range(len(predictions)),
    predictions,
    marker="s",
    label="Predicted Occupancy"
)

plt.title("SmartFlow Parking Availability Prediction")
plt.xlabel("Test Records")
plt.ylabel("Occupied Parking Slots")

plt.legend()
plt.grid(True)

# Save graph
plt.savefig("outputs/parking_prediction_graph.png")

plt.show()

print("Parking prediction graph generated successfully!")
