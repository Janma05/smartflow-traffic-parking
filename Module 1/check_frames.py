
import cv2
from pathlib import Path

# Full path to the online sample traffic video
video_path = Path(
    r"C:\Users\Admin\OneDrive\Desktop\TraffIQ\data\sample videos\Online Traffic Sample.mp4"
)

# Check whether the video file exists
if not video_path.exists():
    print("Error: Video file not found!")
    print("Expected path:", video_path)
    raise SystemExit(1)

print("Video found:", video_path)

# Open the video
cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    print("Error: Could not open the video.")
    print("Check whether the video file is valid.")
    raise SystemExit(1)

# Get video information
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
duration = total_frames / fps if fps > 0 else 0

print("Total frames:", total_frames)
print("FPS:", fps)
print("Duration:", round(duration, 2), "seconds")

# Select five frames from different parts of the video
frame_numbers = [
    int(total_frames * fraction)
    for fraction in [0.1, 0.3, 0.5, 0.7, 0.9]
]

# Save extracted frames inside backend/frame_checks
output_folder = Path(__file__).resolve().parent / "frame_checks"
output_folder.mkdir(parents=True, exist_ok=True)

# Extract and save frames
for number in frame_numbers:
    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
    success, frame = cap.read()

    if success:
        output_path = output_folder / f"frame_{number}.jpg"
        saved = cv2.imwrite(str(output_path), frame)

        if saved:
            print("Saved:", output_path)
        else:
            print("Error saving frame:", number)
    else:
        print("Could not read frame:", number)

# Release video resources
cap.release()

print("\nDone! Check the backend/frame_checks folder.")
