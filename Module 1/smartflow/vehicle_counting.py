
import cv2
from ultralytics import YOLO
from collections import Counter

print("SmartFlow - Vehicle Counting Started")

# Load the YOLO model
model = YOLO("yolo11n.pt")

# Open webcam
cap = cv2.VideoCapture("videos/Traffic video 1.mp4")

if not cap.isOpened():
    print("Error: Could not open traffic video.")
    raise SystemExit

# COCO class IDs for vehicles
vehicle_classes = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

while True:
    ret, frame = cap.read()

    if not ret:
        print("Could not read camera frame.")
        break

    # Detect objects
    results = model(frame, verbose=False)
    counts = Counter()

    # Count detected vehicles
    for box in results[0].boxes:
        class_id = int(box.cls[0])

        if class_id in vehicle_classes:
            counts[vehicle_classes[class_id]] += 1

    # Draw detection boxes
    output = results[0].plot()

    # Display vehicle counts
    y = 35
    for vehicle in ["Car", "Motorcycle", "Bus", "Truck"]:
        text = f"{vehicle}: {counts[vehicle]}"
        cv2.putText(
            output, text, (20, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8,
            (0, 255, 0), 2
        )
        y += 35

    cv2.imshow("SmartFlow - Vehicle Counting", output)

    # Press Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("SmartFlow vehicle counting stopped.")
