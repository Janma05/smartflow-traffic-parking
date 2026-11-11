
import cv2
from ultralytics import YOLO
from pathlib import Path

print("SmartFlow - Traffic Density Monitoring Started")

# Load YOLO model
model = YOLO("yolo11n.pt")

# Load recorded traffic video
video_path = Path(__file__).resolve().parent / "videos" / "Traffic video 1.mp4"
cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    print(f"Error: Could not open video: {video_path}")
    raise SystemExit

print("Traffic video opened successfully.")

# Vehicle class IDs: car, motorcycle, bus, truck
vehicle_classes = {2, 3, 5, 7}

# Track processed frames
frame_number = 0

try:
    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print(f"Video ended or frame could not be read at frame: {frame_number}")
            break

        frame_number += 1
        print(f"Processing frame: {frame_number}")

        # Detect vehicles using YOLO
        results = model(frame, verbose=False)
        vehicle_count = 0

        for box in results[0].boxes:
            class_id = int(box.cls[0])

            if class_id in vehicle_classes:
                vehicle_count += 1

        # Determine traffic density
        # Prototype thresholds; calibrate for your traffic videos
        if vehicle_count <= 2:
            density = "LOW"
            color = (0, 255, 0)
        elif vehicle_count <= 5:
            density = "MEDIUM"
            color = (0, 255, 255)
        else:
            density = "HIGH"
            color = (0, 0, 255)

        # Draw detection boxes
        output = results[0].plot()

        # Display vehicle count
        cv2.putText(
            output,
            f"Vehicles: {vehicle_count}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        # Display traffic density
        cv2.putText(
            output,
            f"Traffic Density: {density}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2
        )

        # Display frame number
        cv2.putText(
            output,
            f"Frame: {frame_number}",
            (20, 115),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )

        # Show output window
        cv2.imshow("SmartFlow - Traffic Density", output)

        # Press Q to stop
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Monitoring stopped by user.")
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

print(f"Total frames processed: {frame_number}")
print("Traffic density monitoring stopped.")
