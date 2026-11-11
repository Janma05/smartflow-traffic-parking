
import pandas as pd

# Load parking dataset
df = pd.read_csv("dataset/parking_data.csv")

print("Original Dataset:")
print(df)

# Check missing values
print("\nMissing Values:")
print(df.isnull().sum())

# Remove duplicate records
df = df.drop_duplicates()

# Convert location into numerical values
df["location"] = df["location"].map({
    "Mall": 0,
    "Office": 1,
    "Hospital": 2
})

# Convert day into numerical values
df["day"] = df["day"].map({
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
})

# Save preprocessed dataset
df.to_csv("dataset/processed_parking_data.csv", index=False)

print("\nPreprocessing Completed Successfully!")
print("\nProcessed Dataset:")
print(df)
