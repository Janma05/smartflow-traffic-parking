
import pandas as pd
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor

# Load preprocessed dataset
df = pd.read_csv("dataset/processed_parking_data.csv")

# Input features
X = df[["location", "day", "hour"]]

# Target variable
y = df["occupied_slots"]

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Create Random Forest model
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

# Train the model
model.fit(X_train, y_train)

# Save trained model
os.makedirs("models", exist_ok=True)

joblib.dump(model, "models/parking_model.pkl")

print("Random Forest Model Trained Successfully!")
print("Training Records:", len(X_train))
print("Testing Records:", len(X_test))
print("Model saved successfully!")
