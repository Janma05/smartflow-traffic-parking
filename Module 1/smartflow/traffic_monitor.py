
import cv2

print("SmartFlow Traffic Monitoring Started")

# Open the default camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not found. We will use a traffic video later.")
else:
    print("Camera opened successfully.")

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow("SmartFlow - Traffic Monitoring", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
