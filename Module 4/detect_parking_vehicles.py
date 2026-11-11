from ultralytics import YOLO
import cv2
import os

# Load YOLO model
model = YOLO("yolo11n.pt")

input_folder = "outputs/parking_frames"
output_folder = "outputs/detected_frames"

os.makedirs(output_folder, exist_ok=True)

# Vehicle class IDs in COCO dataset
vehicle_classes = [2, 3, 5, 7]

for filename in os.listdir(input_folder):

    if filename.endswith(".jpg"):

        image_path = os.path.join(input_folder, filename)

        image = cv2.imread(image_path)

        results = model(image)

        vehicle_count = 0

        for result in results:

            for box in result.boxes:

                class_id = int(box.cls[0])

                if class_id in vehicle_classes:
                    vehicle_count += 1

        print(filename, "Vehicles detected:", vehicle_count)

        annotated_image = results[0].plot()

        cv2.imwrite(
            os.path.join(output_folder, filename),
            annotated_image
        )

print("Vehicle detection completed!")