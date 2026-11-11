import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Load video observations
data = pd.read_csv(
    "dataset/parking_video_observations.csv"
)

# Select input and target
X = data[["elapsed_seconds"]]

y = data["estimated_occupied"]

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

# Evaluate model
predictions = model.predict(X_test)

mae = mean_absolute_error(y_test, predictions)
mse = mean_squared_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("Video-based Parking Model Training Completed!")
print("MAE:", mae)
print("MSE:", mse)
print("R2 Score:", r2)

# Save model
joblib.dump(
    model,
    "models/video_parking_model.pkl"
)

print("Model saved successfully!")