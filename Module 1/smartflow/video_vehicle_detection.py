
import cv2
from ultralytics import YOLO

# Load the trained YOLO model
model = YOLO("yolo11n.pt")

# Open the recorded video
video_path = "videos/Traffic video 1.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

print("SmartFlow video vehicle detection started!")
print("Press Q to stop.")

vehicle_classes = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Detect objects in each frame
    results = model(frame, verbose=False)

    vehicle_counts = {
        "Car": 0,
        "Motorcycle": 0,
        "Bus": 0,
        "Truck": 0
    }

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])

            if class_id in vehicle_classes:
                vehicle_counts[vehicle_classes[class_id]] += 1

    # Draw detection boxes
    output_frame = results[0].plot()

    # Display vehicle counts
    y = 35
    for vehicle, count in vehicle_counts.items():
        cv2.putText(
            output_frame,
            f"{vehicle}: {count}",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        y += 30

    cv2.imshow("SmartFlow - Video Vehicle Detection", output_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("Video vehicle detection completed!")
