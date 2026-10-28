
import cv2

video_path = r"..\data\sample videos\Traffic video 1.mp4"
output_path = "frame_224.jpg"

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    raise RuntimeError(f"Could not open video: {video_path}")

# Frame numbers in the summary start at 1.
# OpenCV frame positions start at 0.
cap.set(cv2.CAP_PROP_POS_FRAMES, 223)

success, frame = cap.read()
cap.release()

if success:
    cv2.imwrite(output_path, frame)
    print(f"Frame saved successfully: {output_path}")
else:
    print("Could not read frame 224.")
