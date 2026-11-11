
import cv2
from pathlib import Path

# ==========================================
# FILE PATHS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR / "videos" / "parking_frame.jpg"
OUTPUT_IMAGE = BASE_DIR / "videos" / "parking_slots_configured.jpg"
OUTPUT_FILE = BASE_DIR / "videos" / "parking_slots.txt"

# ==========================================
# LOAD ORIGINAL IMAGE
# ==========================================
image = cv2.imread(str(IMAGE_PATH))

if image is None:
    print(f"ERROR: Could not load image: {IMAGE_PATH}")
    raise SystemExit(1)

original_height, original_width = image.shape[:2]

# ==========================================
# RESIZE IMAGE LIKE THE SUCCESSFUL TEST
# ==========================================
MAX_WIDTH = 900
MAX_HEIGHT = 500
TOTAL_SLOTS = 10

scale = min(
    MAX_WIDTH / original_width,
    MAX_HEIGHT / original_height,
    1.0
)

display_width = max(1, int(original_width * scale))
display_height = max(1, int(original_height * scale))

display_image = cv2.resize(
    image,
    (display_width, display_height),
    interpolation=cv2.INTER_AREA
)

# ==========================================
# SELECTION VARIABLES
# ==========================================
WINDOW_NAME = "SmartFlow - Select Parking Spaces"

slots = []
drawing = False
start_point = None

# ==========================================
# MOUSE CALLBACK
# ==========================================
def mouse_callback(event, x, y, flags, param):
    global drawing, start_point, display_image

    if event == cv2.EVENT_LBUTTONDOWN:
        if len(slots) >= TOTAL_SLOTS:
            print("All 10 spaces are selected.")
            return

        drawing = True
        start_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        preview = display_image.copy()

        cv2.rectangle(
            preview,
            start_point,
            (x, y),
            (0, 255, 0),
            2
        )

        cv2.imshow(WINDOW_NAME, preview)

    elif event == cv2.EVENT_LBUTTONUP and drawing:
        drawing = False
        end_point = (x, y)

        x1 = min(start_point[0], end_point[0])
        y1 = min(start_point[1], end_point[1])
        x2 = max(start_point[0], end_point[0])
        y2 = max(start_point[1], end_point[1])

        if x2 - x1 < 6 or y2 - y1 < 6:
            print("Rectangle too small. Try again.")
            cv2.imshow(WINDOW_NAME, display_image)
            return

        # Convert display coordinates to original image coordinates
        original_slot = (
            max(0, min(original_width, round(x1 / scale))),
            max(0, min(original_height, round(y1 / scale))),
            max(0, min(original_width, round(x2 / scale))),
            max(0, min(original_height, round(y2 / scale)))
        )

        slots.append(original_slot)
        slot_number = len(slots)

        # Draw selection on the displayed image
        cv2.rectangle(
            display_image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            display_image,
            f"Parking {slot_number}",
            (x1, max(18, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1
        )

        cv2.imshow(WINDOW_NAME, display_image)

        print(f"Selected parking space {slot_number}/{TOTAL_SLOTS}")

        if len(slots) == TOTAL_SLOTS:
            print("All 10 spaces selected. Press Q to save.")

# ==========================================
# DISPLAY WINDOW
# ==========================================
# AUTOSIZE displays the image at its actual resized dimensions.
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)
cv2.setMouseCallback(WINDOW_NAME, mouse_callback)
cv2.imshow(WINDOW_NAME, display_image)

print("\n========================================")
print(" SMARTFLOW PARKING SLOT CONFIGURATION")
print("========================================")
print(f"Original image: {original_width} x {original_height}")
print(f"Displayed image: {display_width} x {display_height}")
print(f"Scale factor: {scale:.4f}")
print("Select 10 parking spaces using your mouse.")
print("Drag from one corner to the opposite corner.")
print("Press Q to save after selecting all 10 spaces.")
print("Press ESC to cancel.")
print("========================================\n")

# ==========================================
# WAIT FOR USER
# ==========================================
cancelled = False

while True:
    key = cv2.waitKey(20) & 0xFF

    if key == ord("q"):
        break

    if key == 27:
        cancelled = True
        break

cv2.destroyAllWindows()

# ==========================================
# SAVE COORDINATES
# ==========================================
if cancelled:
    print("Selection cancelled. No new coordinates saved.")

elif len(slots) != TOTAL_SLOTS:
    print(f"Only {len(slots)} spaces selected.")
    print("Coordinates not saved. Run the script again.")

else:
    # Save original-resolution coordinates
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        for slot in slots:
            file.write(",".join(map(str, slot)) + "\n")

    # Draw the saved rectangles on the original image
    configured_image = image.copy()

    for index, (x1, y1, x2, y2) in enumerate(slots, start=1):
        cv2.rectangle(
            configured_image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            3
        )

        cv2.putText(
            configured_image,
            f"Parking {index}",
            (x1, max(25, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    image_saved = cv2.imwrite(
        str(OUTPUT_IMAGE),
        configured_image
    )

    if image_saved:
        print("\nSUCCESS: Parking spaces configured!")
        print(f"Total spaces: {len(slots)}")
        print(f"Coordinates: {OUTPUT_FILE}")
        print(f"Preview image: {OUTPUT_IMAGE}")
    else:
        print("ERROR: Could not save the configured preview image.")
