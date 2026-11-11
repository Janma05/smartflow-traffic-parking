
import cv2
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
VIDEO_PATH = BASE_DIR / "videos" / "Parking lot 3.mp4"
MODEL_PATH = BASE_DIR / "yolo11n.pt"

CONFIDENCE = 0.10
TILE_SIZE = 960
OVERLAP = 160

model = YOLO(str(MODEL_PATH))
cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {VIDEO_PATH}")

# Read one frame for this test.
ret, frame = cap.read()
cap.release()

if not ret:
    raise RuntimeError("Could not read the first video frame.")

height, width = frame.shape[:2]
print(f"Video frame: {width} x {height}")

output = frame.copy()
step = TILE_SIZE - OVERLAP
total_detections = 0

# Process overlapping crops so small cars appear larger
# during inference.
for y1 in range(0, height, step):
    for x1 in range(0, width, step):
        x2 = min(x1 + TILE_SIZE, width)
        y2 = min(y1 + TILE_SIZE, height)

        # Shift final crops to retain the requested tile size.
        x_start = max(0, x2 - TILE_SIZE)
        y_start = max(0, y2 - TILE_SIZE)

        crop = frame[y_start:y2, x_start:x2]

        if crop.size == 0:
            continue

        results = model.predict(
            source=crop,
            imgsz=960,
            conf=CONFIDENCE,
            verbose=False
        )

        result = results[0]

        if result.boxes is None:
            continue

        for box in result.boxes:
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())

            # COCO vehicle classes.
            if class_id not in {2, 3, 5, 7}:
                continue

            bx1, by1, bx2, by2 = map(
                int, box.xyxy[0].tolist()
            )

            # Convert crop coordinates to original-frame coordinates.
            bx1 += x_start
            bx2 += x_start
            by1 += y_start
            by2 += y_start

            total_detections += 1

            name = model.names[class_id]
            print(
                f"{name}: confidence={confidence:.2f}, "
                f"box=({bx1}, {by1}, {bx2}, {by2})"
            )

            cv2.rectangle(
                output,
                (bx1, by1),
                (bx2, by2),
                (0, 255, 255),
                2
            )

            cv2.putText(
                output,
                f"{name} {confidence:.2f}",
                (bx1, max(20, by1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                2
            )

print(f"\nTotal vehicle detections across tiles: {total_detections}")

# Save a full-resolution result for inspection.
output_path = BASE_DIR / "yolo_tile_test.jpg"
cv2.imwrite(str(output_path), output)
print(f"Saved detection image: {output_path}")

# Display a resized preview.
scale = min(1100 / width, 650 / height, 1.0)
preview = cv2.resize(
    output,
    (int(width * scale), int(height * scale))
)

cv2.imshow("SmartFlow - YOLO Tile Detection Test", preview)
cv2.waitKey(0)
cv2.destroyAllWindows()
