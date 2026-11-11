from ultralytics import YOLO
import cv2
import os
import csv
import re
from parking_config import TOTAL_PARKING_SLOTS

model = YOLO("yolo11n.pt")

input_folder = "outputs/parking_frames"
output_file = "dataset/parking_video_observations.csv"

vehicle_classes = [2, 3, 5, 7]

files = [
    f for f in os.listdir(input_folder)
    if f.endswith(".jpg")
]

files.sort(
    key=lambda f: int(re.search(r"\d+", f).group())
)

with open(output_file, "w", newline="") as file:
    writer = csv.writer(file)

    writer.writerow([
        "frame_name",
        "elapsed_seconds",
        "vehicle_count",
        "total_slots",
        "estimated_occupied",
        "estimated_available"
    ])

    for filename in files:
        image_path = os.path.join(input_folder, filename)
        image = cv2.imread(image_path)

        results = model(image, verbose=False)

        vehicle_count = 0

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id in vehicle_classes:
                    vehicle_count += 1

        estimated_occupied = min(
            vehicle_count, TOTAL_PARKING_SLOTS
        )

        estimated_available = (
            TOTAL_PARKING_SLOTS - estimated_occupied
        )

        frame_number = int(
            re.search(r"\d+", filename).group()
        )

        writer.writerow([
            filename,
            frame_number * 2,
            vehicle_count,
            TOTAL_PARKING_SLOTS,
            estimated_occupied,
            estimated_available
        ])

print("Parking availability dataset created!")