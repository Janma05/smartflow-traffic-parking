
import cv2
from pathlib import Path
from app.vehicle_detection import VehicleDetector

# Use folders relative to this script
backend_folder = Path(__file__).resolve().parent

frames_folder = backend_folder / "frame_checks"
output_folder = backend_folder / "detection_results_online"

# Check that extracted frames exist
if not frames_folder.exists():
    print("Error: frame_checks folder not found!")
    raise SystemExit(1)

image_paths = sorted(frames_folder.glob("frame_*.jpg"))

if not image_paths:
    print("Error: No extracted frames found in frame_checks!")
    raise SystemExit(1)

# Create output folder
output_folder.mkdir(parents=True, exist_ok=True)

# Initialize vehicle detector
detector = VehicleDetector()

print("Starting vehicle detection validation...")
print("Frames to process:", len(image_paths))

for image_path in image_paths:
    frame = cv2.imread(str(image_path))

    if frame is None:
        print(f"Could not read image: {image_path.name}")
        continue

    # Run YOLO vehicle detection and tracking
    annotated, counts, tracks = detector.process_frame(frame)

    total_vehicles = sum(counts.values())

    # Save annotated image
    output_path = output_folder / image_path.name
    saved = cv2.imwrite(str(output_path), annotated)

    print(f"\nFrame: {image_path.name}")
    print("Vehicle counts:", counts)
    print("Total detected:", total_vehicles)
    print("Tracked vehicles:", len(tracks))

    if saved:
        print("Saved annotated image:", output_path)
    else:
        print("Error saving annotated image!")

print("\nDetection validation completed!")
print("Open the detection_results_online folder to inspect the results.")
