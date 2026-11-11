
import cv2
import os

video_path = os.path.join(
    "videos", "video1.mp4"
)

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("ERROR: Could not open the video.")
    print("Check the filename and videos folder.")
    exit()

print("Video opened successfully!")

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)

print("Video FPS:", fps)
print("Total frames:", int(total_frames))

while True:
    ret, frame = cap.read()

    if not ret:
        break

    cv2.imshow("SmartFlow - Video Test", frame)

    if cv2.waitKey(25) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("Video test completed.")
