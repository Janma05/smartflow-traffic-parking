import cv2
import os

video_path = "videos/Parking lot 1.mp4"

output_folder = "outputs/parking_frames"
os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open parking video")
    exit()

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

print("Video opened successfully")
print("Total frames:", total_frames)
print("FPS:", fps)

frame_number = 0
saved_count = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    if frame_number % int(fps * 2) == 0:
        filename = f"{output_folder}/frame_{saved_count}.jpg"
        cv2.imwrite(filename, frame)
        saved_count += 1

    frame_number += 1

cap.release()

print("Frame extraction completed!")
print("Total images saved:", saved_count)