
import cv2
import json
from pathlib import Path
from ultralytics import YOLO

print("SmartFlow - Vehicle Detection, ByteTrack and Parking Started")

# =====================================================
# 1. FILE PATHS
# =====================================================
BASE_DIR = Path(__file__).resolve().parent

VIDEO_PATH = BASE_DIR / "videos" / "Parking lot 3.mp4"
MODEL_PATH = BASE_DIR / "yolo11n.pt"
PARKING_FILE = BASE_DIR / "parking_spaces.json"

WINDOW_NAME = "SmartFlow - Parking Occupancy"

# =====================================================
# 2. CONFIGURATION
# =====================================================
# COCO classes:
# 2 = car, 3 = motorcycle, 5 = bus, 7 = truck
VEHICLE_CLASSES = {2, 3, 5, 7}

VEHICLE_NAMES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck",
}

# Lower confidence can help with small aerial vehicles.
DETECTION_CONFIDENCE = 0.05

# Higher resolution can help detect smaller vehicles,
# but it requires more memory and processing time.
IMAGE_SIZE = 1920

OCCUPANCY_THRESHOLD = 0.05
SPACE_PADDING = 5

MAX_DISPLAY_WIDTH = 1100
MAX_DISPLAY_HEIGHT = 650

PANEL_ALPHA = 0.60
DEBUG_INTERVAL = 30

# OpenCV uses BGR color order.
OCCUPIED_COLOR = (0, 255, 0)       # GREEN
AVAILABLE_COLOR = (255, 0, 0)      # BLUE
INVALID_COLOR = (0, 165, 255)      # ORANGE
WHITE = (255, 255, 255)
YELLOW = (0, 255, 255)


# =====================================================
# 3. DRAW TRANSPARENT PANEL
# =====================================================
def draw_transparent_panel(
    frame, x, y, width, height, alpha=PANEL_ALPHA
):
    overlay = frame.copy()
    frame_h, frame_w = frame.shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(frame_w, x + width)
    y2 = min(frame_h, y + height)

    if x2 <= x1 or y2 <= y1:
        return

    cv2.rectangle(
        overlay,
        (x1, y1),
        (x2, y2),
        (0, 0, 0),
        -1,
    )

    cv2.addWeighted(
        overlay,
        alpha,
        frame,
        1.0 - alpha,
        0,
        frame,
    )


# =====================================================
# 4. LOAD PARKING SPACES
# =====================================================
def load_parking_spaces(file_path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"Parking-space file not found:\n{file_path}"
        )

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get(
            "spaces",
            data.get("parking_spaces", []),
        )

    if not isinstance(data, list):
        raise ValueError(
            "Parking JSON must contain a list of spaces."
        )

    spaces = []

    for index, item in enumerate(data, start=1):
        if isinstance(item, dict):
            if all(
                k in item for k in ("x1", "y1", "x2", "y2")
            ):
                coords = (
                    item["x1"], item["y1"],
                    item["x2"], item["y2"],
                )

            elif all(
                k in item for k in ("x", "y", "w", "h")
            ):
                x, y, w, h = (
                    item["x"], item["y"],
                    item["w"], item["h"],
                )
                coords = (x, y, x + w, y + h)

            else:
                raise ValueError(
                    f"Invalid coordinate format for space {index}."
                )

        elif isinstance(item, (list, tuple)) and len(item) == 4:
            coords = item

        else:
            raise ValueError(
                f"Invalid format for space {index}."
            )

        try:
            x1, y1, x2, y2 = map(int, coords)
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid numeric coordinates for space {index}."
            )

        if x2 <= x1 or y2 <= y1:
            raise ValueError(
                f"Invalid rectangle for space {index}."
            )

        spaces.append((x1, y1, x2, y2))

    if not spaces:
        raise ValueError("No parking spaces were loaded.")

    print(f"Loaded parking spaces: {len(spaces)}")

    for i, space in enumerate(spaces, start=1):
        print(f"Space {i}: {space}")

    return spaces


# =====================================================
# 5. PARKING OCCUPANCY CHECK
# =====================================================
def check_occupancy(space, vehicle_boxes):
    sx1, sy1, sx2, sy2 = space

    # Allow a small coordinate tolerance.
    sx1 -= SPACE_PADDING
    sy1 -= SPACE_PADDING
    sx2 += SPACE_PADDING
    sy2 += SPACE_PADDING

    space_area = max(
        1,
        (sx2 - sx1) * (sy2 - sy1),
    )

    for box in vehicle_boxes:
        vx1, vy1, vx2, vy2 = map(int, box)

        # Method 1: Bounding-box intersection.
        ix1 = max(sx1, vx1)
        iy1 = max(sy1, vy1)
        ix2 = min(sx2, vx2)
        iy2 = min(sy2, vy2)

        if ix2 > ix1 and iy2 > iy1:
            intersection = (
                (ix2 - ix1) * (iy2 - iy1)
            )

            if intersection / space_area >= OCCUPANCY_THRESHOLD:
                return True

        # Method 2: Vehicle center inside parking space.
        center_x = (vx1 + vx2) // 2
        center_y = (vy1 + vy2) // 2

        if (
            sx1 <= center_x <= sx2
            and sy1 <= center_y <= sy2
        ):
            return True

        # Method 3: Vehicle lower-center point inside space.
        bottom_x = (vx1 + vx2) // 2
        bottom_y = vy2

        if (
            sx1 <= bottom_x <= sx2
            and sy1 <= bottom_y <= sy2
        ):
            return True

    return False


# =====================================================
# 6. VALIDATE FILES
# =====================================================
if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"YOLO model not found:\n{MODEL_PATH}"
    )

if not VIDEO_PATH.exists():
    raise FileNotFoundError(
        f"Video not found:\n{VIDEO_PATH}"
    )

parking_spaces = load_parking_spaces(PARKING_FILE)

print("\nLoading YOLO model...")
model = YOLO(str(MODEL_PATH))

cap = cv2.VideoCapture(str(VIDEO_PATH))

if not cap.isOpened():
    raise RuntimeError(
        f"Unable to open video:\n{VIDEO_PATH}"
    )

video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
video_fps = cap.get(cv2.CAP_PROP_FPS)

print(f"Video resolution: {video_width} x {video_height}")
print(f"Video FPS: {video_fps:.2f}")
print(f"Confidence: {DETECTION_CONFIDENCE}")
print(f"Inference image size: {IMAGE_SIZE}")
print("GREEN = Occupied | BLUE = Available")
print("Press Q or ESC to stop.")

for i, (x1, y1, x2, y2) in enumerate(
    parking_spaces, start=1
):
    if (
        x1 < 0 or y1 < 0
        or x2 > video_width or y2 > video_height
    ):
        print(
            f"WARNING: Parking space {i} is outside "
            "the video boundaries."
        )

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(
    WINDOW_NAME,
    MAX_DISPLAY_WIDTH,
    MAX_DISPLAY_HEIGHT,
)

frame_number = 0
unique_vehicle_ids = set()


# =====================================================
# 7. VIDEO PROCESSING
# =====================================================
try:
    while True:
        ret, frame = cap.read()

        if not ret or frame is None:
            print("Video finished.")
            break

        frame_number += 1

        # ---------------------------------------------
        # YOLO + BYTETRACK
        #
        # Do not apply the vehicle class filter here.
        # First inspect all model detections, then select
        # the vehicle classes below.
        # ---------------------------------------------
        results = model.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=DETECTION_CONFIDENCE,
            imgsz=IMAGE_SIZE,
            verbose=False,
        )

        result = results[0]

        # Start with the original frame and draw only the
        # selected vehicle detections ourselves.
        output = frame.copy()

        vehicle_boxes = []
        vehicle_ids = []
        vehicle_classes = []
        vehicle_confidences = []

        raw_detection_count = (
            0
            if result.boxes is None
            else len(result.boxes)
        )

        # ---------------------------------------------
        # EXTRACT VEHICLE DETECTIONS
        # ---------------------------------------------
        if result.boxes is not None and raw_detection_count > 0:
            all_boxes = result.boxes.xyxy.cpu().numpy()
            all_classes = result.boxes.cls.int().cpu().tolist()
            all_confidences = (
                result.boxes.conf.cpu().numpy().tolist()
            )

            if result.boxes.id is not None:
                all_ids = result.boxes.id.int().cpu().tolist()
            else:
                all_ids = [None] * len(all_boxes)

            for box, class_id, confidence, track_id in zip(
                all_boxes,
                all_classes,
                all_confidences,
                all_ids,
            ):
                # Keep only cars, motorcycles, buses and trucks.
                if class_id not in VEHICLE_CLASSES:
                    continue

                vehicle_boxes.append(box)
                vehicle_classes.append(class_id)
                vehicle_confidences.append(confidence)
                vehicle_ids.append(track_id)

                if track_id is not None:
                    unique_vehicle_ids.add(track_id)

                vx1, vy1, vx2, vy2 = map(int, box)

                # Draw vehicle bounding box.
                cv2.rectangle(
                    output,
                    (vx1, vy1),
                    (vx2, vy2),
                    YELLOW,
                    2,
                )

                vehicle_name = VEHICLE_NAMES[class_id]

                if track_id is None:
                    label = (
                        f"{vehicle_name} {confidence:.2f}"
                    )
                else:
                    label = (
                        f"{vehicle_name} ID:{track_id} "
                        f"{confidence:.2f}"
                    )

                label_y = max(20, vy1 - 7)

                cv2.putText(
                    output,
                    label,
                    (vx1, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.50,
                    YELLOW,
                    2,
                    cv2.LINE_AA,
                )

        # ---------------------------------------------
        # VEHICLE CATEGORY COUNTS
        # ---------------------------------------------
        class_counts = {
            class_id: 0 for class_id in VEHICLE_CLASSES
        }

        for class_id in vehicle_classes:
            class_counts[class_id] += 1

        # ---------------------------------------------
        # PARKING OCCUPANCY
        # ---------------------------------------------
        occupied_count = 0
        space_statuses = []

        for index, space in enumerate(parking_spaces, start=1):
            x1, y1, x2, y2 = space

            valid_space = (
                x1 >= 0
                and y1 >= 0
                and x2 <= video_width
                and y2 <= video_height
            )

            if not valid_space:
                status = "Invalid"
                color = INVALID_COLOR
                label = f"Check Space {index}"

            else:
                occupied = check_occupancy(
                    space,
                    vehicle_boxes,
                )

                if occupied:
                    status = "Occupied"
                    occupied_count += 1
                    color = OCCUPIED_COLOR
                    label = f"Occupied {index}"
                else:
                    status = "Available"
                    color = AVAILABLE_COLOR
                    label = f"Available {index}"

            space_statuses.append(status)

            cv2.rectangle(
                output,
                (x1, y1),
                (x2, y2),
                color,
                3,
            )

            label_y = y1 - 8 if y1 >= 25 else y1 + 20

            cv2.putText(
                output,
                label,
                (x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.60,
                color,
                2,
                cv2.LINE_AA,
            )

        total_spaces = len(parking_spaces)
        available_count = total_spaces - occupied_count

        # ---------------------------------------------
        # DEBUG OUTPUT
        # ---------------------------------------------
        if frame_number % DEBUG_INTERVAL == 0:
            print("\n========== SMARTFLOW DETECTION DEBUG ==========")
            print(f"Frame: {frame_number}")
            print(f"Raw model detections: {raw_detection_count}")
            print(f"Vehicle detections: {len(vehicle_boxes)}")
            print(f"Occupied spaces: {occupied_count}")
            print(f"Available spaces: {available_count}")

            for i, (box, class_id, confidence, track_id) in enumerate(
                zip(
                    vehicle_boxes,
                    vehicle_classes,
                    vehicle_confidences,
                    vehicle_ids,
                ),
                start=1,
            ):
                print(
                    f"Vehicle {i}: "
                    f"class={VEHICLE_NAMES[class_id]}, "
                    f"confidence={confidence:.3f}, "
                    f"ID={track_id}, "
                    f"box={box.astype(int).tolist()}"
                )

            print("Parking-space status:")

            for i, (space, status) in enumerate(
                zip(parking_spaces, space_statuses),
                start=1,
            ):
                print(
                    f"Space {i} {space}: {status}"
                )

            if raw_detection_count == 0:
                print(
                    "WARNING: YOLO returned no detections "
                    "for this frame."
                )
            elif len(vehicle_boxes) == 0:
                print(
                    "WARNING: YOLO detected objects, but none "
                    "belonged to vehicle classes 2, 3, 5 or 7."
                )

        # ---------------------------------------------
        # TRANSPARENT INFORMATION PANEL
        # ---------------------------------------------
        panel_width = min(550, video_width - 16)
        panel_height = 280

        draw_transparent_panel(
            output,
            8,
            8,
            panel_width,
            panel_height,
        )

        information = [
            (f"Occupied: {occupied_count}", OCCUPIED_COLOR),
            (f"Available: {available_count}", (255, 160, 50)),
            (f"Total spaces: {total_spaces}", WHITE),
            (f"Raw YOLO detections: {raw_detection_count}", YELLOW),
            (f"Vehicles detected: {len(vehicle_boxes)}", YELLOW),
            (f"Tracked vehicle IDs: {len(unique_vehicle_ids)}", YELLOW),
            (f"Frame: {frame_number}", WHITE),
        ]

        y_position = 38

        for info_text, info_color in information:
            cv2.putText(
                output,
                info_text,
                (22, y_position),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,
                info_color,
                2,
                cv2.LINE_AA,
            )
            y_position += 34

        # ---------------------------------------------
        # CATEGORY COUNTS
        # ---------------------------------------------
        category_text = " | ".join(
            f"{VEHICLE_NAMES[c]}: {class_counts[c]}"
            for c in VEHICLE_NAMES
        )

        cv2.putText(
            output,
            category_text,
            (20, min(video_height - 15, 310)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            WHITE,
            2,
            cv2.LINE_AA,
        )

        # ---------------------------------------------
        # RESIZE FOR DISPLAY
        # ---------------------------------------------
        frame_h, frame_w = output.shape[:2]

        scale = min(
            MAX_DISPLAY_WIDTH / frame_w,
            MAX_DISPLAY_HEIGHT / frame_h,
            1.0,
        )

        display_w = max(1, int(frame_w * scale))
        display_h = max(1, int(frame_h * scale))

        display_frame = cv2.resize(
            output,
            (display_w, display_h),
            interpolation=cv2.INTER_AREA,
        )

        cv2.imshow(WINDOW_NAME, display_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

    print("\n========== SMARTFLOW SUMMARY ==========")
    print(f"Frames processed: {frame_number}")
    print(f"Unique vehicle IDs: {len(unique_vehicle_ids)}")
    print(f"Total parking spaces: {len(parking_spaces)}")
    print("SmartFlow parking monitoring stopped.")
