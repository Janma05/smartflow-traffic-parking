import pandas as pd
import matplotlib.pyplot as plt

data = pd.read_csv("dataset/parking_video_observations.csv")

plt.figure(figsize=(10, 5))

plt.plot(
    data["elapsed_seconds"],
    data["estimated_occupied"],
    marker="o",
    label="Estimated Occupied Slots"
)

plt.plot(
    data["elapsed_seconds"],
    data["estimated_available"],
    marker="s",
    label="Estimated Available Slots"
)

plt.title("SmartFlow - Video-Based Parking Analysis")
plt.xlabel("Video Time (Seconds)")
plt.ylabel("Estimated Parking Slots")
plt.legend()
plt.grid(True)

plt.savefig("outputs/video_parking_visualization.png")
plt.show()

print("Parking visualization saved successfully!")