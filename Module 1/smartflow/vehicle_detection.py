
import cv2
from ultralytics import YOLO

print("SmartFlow AI Vehicle Detection Started")

# Load the YOLO model
model = YOLO("yolo11n.pt")

# Open the webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

while True:
    ret, frame = cap.read()

    if not ret:
        print("Could not read camera frame.")
        break

    # Detect objects in the camera frame
    results = model(frame, verbose=False)

    # Draw detection boxes and labels
    annotated_frame = results[0].plot()

    cv2.imshow(
        "SmartFlow - AI Vehicle Detection",
        annotated_frame
    )

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Vehicle detection stopped.")
