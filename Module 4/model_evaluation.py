
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score

# Load dataset
df = pd.read_csv("dataset/processed_parking_data.csv")

# Input and output features
X = df[["location", "day", "hour"]]
y = df["occupied_slots"]

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Load trained model
model = joblib.load("models/parking_model.pkl")

# Make predictions
y_pred = model.predict(X_test)

# Calculate evaluation metrics
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

# Display results
print("PARKING MODEL EVALUATION")
print("------------------------")
print("Mean Absolute Error (MAE):", round(mae, 2))
print("Mean Squared Error (MSE):", round(mse, 2))
print("R2 Score:", round(r2, 2))

print("\nActual vs Predicted Occupancy:")

for actual, predicted in zip(y_test, y_pred):
    print(
        "Actual:", actual,
        "| Predicted:", round(predicted, 2)
    )
