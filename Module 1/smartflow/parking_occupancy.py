
import cv2
from pathlib import Path
from ultralytics import YOLO

print("SmartFlow - YOLO Parking Occupancy Detection Started")

# ==========================================
# FILE PATHS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
SLOTS_FILE = BASE_DIR / "videos" / "parking_slots.txt"
VIDEO_PATH = BASE_DIR / "videos" / "Parking lot 3.mp4"
MODEL_PATH = BASE_DIR / "yolo11n.pt"

# Display settings
MAX_DISPLAY_WIDTH = 1100
MAX_DISPLAY_HEIGHT = 650

# Detection settings
CONFIDENCE_THRESHOLD = 0.15
INFERENCE_SIZE = 960
TILE_WIDTH = 1280
TILE_HEIGHT = 720
TILE_OVERLAP = 0.20

# Occupancy settings
# A detection must cover at least this fraction of a slot.
SLOT_OVERLAP_THRESHOLD = 0.25

# A vehicle must have at least this fraction of its box
# inside a slot before it can mark the slot occupied.
VEHICLE_OVERLAP_THRESHOLD = 0.60

# Dashboard settings
DASHBOARD_ALPHA = 0.30
SLOT_THICKNESS = 5
LABEL_FONT_SCALE = 0.75
COUNTER_FONT_SCALE = 1.35

VEHICLE_CLASSES = [2, 3, 5, 7]

GREEN = (0, 255, 0)
RED = (0, 0, 255)
WHITE = (255, 255, 255)
YELLOW = (0, 255, 255)
BLUE = (255, 120, 0)

# ==========================================
# LOAD PARKING SLOTS
# ==========================================
slots = []

try:
    with open(SLOTS_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            values = [int(value) for value in line.split(",")]
            if len(values) == 4:
                slots.append(tuple(values))

except FileNotFoundError:
    print(f"ERROR: Parking slots file not found: {SLOTS_FILE}")
    print("Configure parking spaces for Parking lot 3 first.")
    raise SystemExit(1)

if not slots:
    print("ERROR: No valid parking spaces configured.")
    raise SystemExit(1)

print(f"Configured parking spaces: {len(slots)}")

# ==========================================
# LOAD MODEL
# ==========================================
if not MODEL_PATH.exists():
    print(f"ERROR: YOLO model not found: {MODEL_PATH}")
    raise SystemExit(1)

model = YOLO(str(MODEL_PATH))

# ==========================================
# TILED VEHICLE DETECTION
# ==========================================
def detect_vehicles_tiled(frame):
    height, width = frame.shape[:2]

    tile_width = min(TILE_WIDTH, width)
    tile_height = min(TILE_HEIGHT, height)

    step_x = max(1, int(tile_width * (1 - TILE_OVERLAP)))
    step_y = max(1, int(tile_height * (1 - TILE_OVERLAP)))

    x_positions = list(range(
        0, max(1, width - tile_width + 1), step_x
    ))
    y_positions = list(range(
        0, max(1, height - tile_height + 1), step_y
    ))

    last_x = max(0, width - tile_width)
    last_y = max(0, height - tile_height)

    if not x_positions or x_positions[-1] != last_x:
        x_positions.append(last_x)

    if not y_positions or y_positions[-1] != last_y:
        y_positions.append(last_y)

    detections = []

    for y in sorted(set(y_positions)):
        for x in sorted(set(x_positions)):
            tile = frame[y:y + tile_height, x:x + tile_width]

            result = model.predict(
                source=tile,
                conf=CONFIDENCE_THRESHOLD,
                imgsz=INFERENCE_SIZE,
                classes=VEHICLE_CLASSES,
                verbose=False
            )[0]

            for box in result.boxes:
                tx1, ty1, tx2, ty2 = map(
                    int, box.xyxy[0].tolist()
                )

                vx1 = max(0, min(width - 1, tx1 + x))
                vy1 = max(0, min(height - 1, ty1 + y))
                vx2 = max(0, min(width, tx2 + x))
                vy2 = max(0, min(height, ty2 + y))

                if vx2 > vx1 and vy2 > vy1:
                    detections.append((vx1, vy1, vx2, vy2))

    # Remove duplicate detections caused by overlapping tiles.
    if not detections:
        return []

    boxes = [
        [x1, y1, x2 - x1, y2 - y1]
        for x1, y1, x2, y2 in detections
    ]

    scores = [1.0] * len(boxes)

    keep = cv2.dnn.NMSBoxes(
        boxes,
        scores,
        score_threshold=0.0,
        nms_threshold=0.45
    )

    if len(keep) == 0:
        return []

    return [detections[int(i)] for i in keep.flatten()]


# ==========================================
# PARKING SLOT OCCUPANCY
# ==========================================
def check_slot_occupied(slot, vehicles):
    sx1, sy1, sx2, sy2 = slot
    slot_area = max(1, (sx2 - sx1) * (sy2 - sy1))

    for vx1, vy1, vx2, vy2 in vehicles:
        ix1 = max(sx1, vx1)
        iy1 = max(sy1, vy1)
        ix2 = min(sx2, vx2)
        iy2 = min(sy2, vy2)

        if ix2 <= ix1 or iy2 <= iy1:
            continue

        intersection_area = (ix2 - ix1) * (iy2 - iy1)
        vehicle_area = max(
            1, (vx2 - vx1) * (vy2 - vy1)
        )

        slot_overlap = intersection_area / slot_area
        vehicle_overlap = intersection_area / vehicle_area

        # Require meaningful overlap instead of simply checking
        # whether a vehicle's center falls inside a slot.
        if (
            slot_overlap >= SLOT_OVERLAP_THRESHOLD
            and vehicle_overlap >= VEHICLE_OVERLAP_THRESHOLD
        ):
            return True

    return False


# ==========================================
# OPEN VIDEO
# ==========================================
cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    print(f"ERROR: Could not open video: {VIDEO_PATH}")
    raise SystemExit(1)

WINDOW_NAME = "SmartFlow - Parking Occupancy Dashboard"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

print(f"Video: {VIDEO_PATH}")
print("Parking monitoring started. Press Q to stop.")
print("Green = Available | Red = Occupied")

frame_number = 0

try:
    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("Video finished.")
            break

        frame_number += 1
        height, width = frame.shape[:2]

        # ==========================================
        # DETECT VEHICLES
        # ==========================================
        vehicles = detect_vehicles_tiled(frame)

        if frame_number % 10 == 1:
            print(
                f"Frame {frame_number}: "
                f"{len(vehicles)} vehicles detected"
            )

        # ==========================================
        # CHECK PARKING SPACES
        # ==========================================
        occupied_count = 0
        available_count = 0
        slot_results = []

        for index, (rx1, ry1, rx2, ry2) in enumerate(slots, start=1):
            sx1 = max(0, min(rx1, width - 1))
            sy1 = max(0, min(ry1, height - 1))
            sx2 = max(0, min(rx2, width))
            sy2 = max(0, min(ry2, height))

            if sx2 <= sx1 or sy2 <= sy1:
                continue

            occupied = check_slot_occupied(
                (sx1, sy1, sx2, sy2),
                vehicles
            )

            if occupied:
                occupied_count += 1
                color = RED
                status = "OCCUPIED"
            else:
                available_count += 1
                color = GREEN
                status = "AVAILABLE"

            slot_results.append(
                (index, sx1, sy1, sx2, sy2, color, status)
            )

        # ==========================================
        # DRAW VEHICLE BOXES
        # ==========================================
        for vx1, vy1, vx2, vy2 in vehicles:
            cv2.rectangle(
                frame,
                (vx1, vy1),
                (vx2, vy2),
                BLUE,
                2
            )

        # ==========================================
        # DRAW PARKING SLOT OUTLINES AND LABELS
        # ==========================================
        for index, sx1, sy1, sx2, sy2, color, status in slot_results:
            cv2.rectangle(
                frame,
                (sx1, sy1),
                (sx2, sy2),
                color,
                SLOT_THICKNESS
            )

            label = f"P{index}: {status}"

            (text_width, text_height), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                LABEL_FONT_SCALE,
                2
            )

            label_x = max(
                0, min(sx1, width - text_width - 8)
            )

            label_y = sy1 - 8

            if label_y - text_height - baseline < 0:
                label_y = min(
                    height - baseline - 2,
                    sy1 + text_height + 12
                )

            top = max(0, label_y - text_height - 8)
            bottom = min(height - 1, label_y + baseline)
            right = min(width - 1, label_x + text_width + 8)

            cv2.rectangle(
                frame,
                (label_x, top),
                (right, bottom),
                color,
                -1
            )

            cv2.putText(
                frame,
                label,
                (label_x + 4, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                LABEL_FONT_SCALE,
                WHITE,
                2,
                cv2.LINE_AA
            )

        # ==========================================
        # CALCULATE COUNTERS
        # ==========================================
        total_slots = occupied_count + available_count

        occupancy_percentage = (
            occupied_count / total_slots * 100
            if total_slots else 0.0
        )

        # ==========================================
        # SEMI-TRANSPARENT DASHBOARD
        # ==========================================
        overlay = frame.copy()

        panel_right = min(700, width - 1)
        panel_bottom = min(350, height - 1)

        cv2.rectangle(
            overlay,
            (12, 12),
            (panel_right, panel_bottom),
            (25, 25, 25),
            -1
        )

        cv2.addWeighted(
            overlay,
            DASHBOARD_ALPHA,
            frame,
            1.0 - DASHBOARD_ALPHA,
            0,
            frame
        )

        counter_rows = [
            (f"Total Spaces: {total_slots}", WHITE, 75),
            (f"Occupied: {occupied_count}", RED, 145),
            (f"Available: {available_count}", GREEN, 215),
            (f"Occupancy: {occupancy_percentage:.1f}%", YELLOW, 285)
        ]

        for text, color, y_position in counter_rows:
            cv2.putText(
                frame,
                text,
                (30, y_position),
                cv2.FONT_HERSHEY_SIMPLEX,
                COUNTER_FONT_SCALE,
                color,
                4,
                cv2.LINE_AA
            )

        cv2.putText(
            frame,
            f"Vehicles detected: {len(vehicles)}",
            (25, min(390, height - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            WHITE,
            2,
            cv2.LINE_AA
        )

        # ==========================================
        # RESIZE FOR DISPLAY ONLY
        # ==========================================
        scale = min(
            MAX_DISPLAY_WIDTH / width,
            MAX_DISPLAY_HEIGHT / height,
            1.0
        )

        display_width = max(1, int(width * scale))
        display_height = max(1, int(height * scale))

        display_frame = cv2.resize(
            frame,
            (display_width, display_height),
            interpolation=cv2.INTER_AREA
        )

        cv2.imshow(WINDOW_NAME, display_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

print(f"Frames processed: {frame_number}")
print("Parking occupancy monitoring stopped.")
