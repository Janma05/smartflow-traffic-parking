
import cv2
from pathlib import Path

# Video and output paths
BASE_DIR = Path(__file__).resolve().parent
VIDEO_PATH = BASE_DIR / "videos" / "Parking lot 3.mp4"
FRAME_PATH = BASE_DIR / "videos" / "parking_frame.jpg"

# Open parking video
cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    print(f"Error: Could not open video: {VIDEO_PATH}")
    raise SystemExit(1)

# Read one frame
success, frame = cap.read()
cap.release()

if not success or frame is None:
    print("Error: Could not read a frame from the video.")
    raise SystemExit(1)

# Save the original-resolution frame for accurate slot coordinates
if not cv2.imwrite(str(FRAME_PATH), frame):
    print("Error: Could not save the parking frame.")
    raise SystemExit(1)

# Resize a separate copy for full-screen viewing
height, width = frame.shape[:2]
max_width = 1000
max_height = 600

scale = min(max_width / width, max_height / height, 1.0)
display_width = int(width * scale)
display_height = int(height * scale)

display_frame = cv2.resize(
    frame,
    (display_width, display_height),
    interpolation=cv2.INTER_AREA
)

# Show the complete frame in a correctly sized window
window_name = "Parking Lot 3 - Full Frame"
cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
cv2.imshow(window_name, display_frame)

print(f"Original frame size: {width} x {height}")
print(f"Display size: {display_width} x {display_height}")
print(f"Full frame saved to: {FRAME_PATH}")
print("Press any key while the image window is active to close it.")

cv2.waitKey(0)
cv2.destroyAllWindows()

print("Parking frame capture completed.")
