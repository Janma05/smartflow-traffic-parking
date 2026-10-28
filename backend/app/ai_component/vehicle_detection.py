from pathlib import Path

import cv2
from ultralytics import YOLO


# YOLO COCO vehicle class IDs
VEHICLE_CLASSES = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


# OpenCV uses BGR colour format.
VEHICLE_COLORS = {
    "car": (0, 100, 0),            # Dark Green
    "truck": (0, 165, 255),        # Orange
    "motorcycle": (255, 0, 255),   # Purple
    "bus": (0, 0, 255),            # Red
    "bicycle": (255, 255, 0),      # Cyan
}


# Resolve model path relative to the backend folder.
MODEL_PATH = Path(__file__).resolve().parents[2] / "yolo11n.pt"


def _overlaps(rect1, rect2, padding=2):
    """Return True when two label rectangles overlap."""

    ax1, ay1, ax2, ay2 = rect1
    bx1, by1, bx2, by2 = rect2

    return not (
        ax2 + padding <= bx1
        or bx2 + padding <= ax1
        or ay2 + padding <= by1
        or by2 + padding <= ay1
    )


class VehicleDetector:
    """Detect and track vehicles with coloured bounding boxes."""

    def __init__(
        self,
        model_path=None,
        confidence=0.15,
        use_tracking=True,
    ):
        resolved_model_path = (
            Path(model_path) if model_path else MODEL_PATH
        )

        if not resolved_model_path.is_file():
            raise FileNotFoundError(
                f"YOLO model not found: {resolved_model_path}"
            )

        self.model = YOLO(str(resolved_model_path))
        self.confidence = float(confidence)
        self.use_tracking = use_tracking

    def process_frame(self, frame):
        """
        Detect vehicles and return:
        annotated frame, vehicle counts, and tracking information.
        """

        annotated = frame.copy()

        # Run YOLO detection or ByteTrack tracking.
        if self.use_tracking:
            results = self.model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=list(VEHICLE_CLASSES.keys()),
                conf=self.confidence,
                verbose=False,
            )
        else:
            results = self.model.predict(
                frame,
                classes=list(VEHICLE_CLASSES.keys()),
                conf=self.confidence,
                verbose=False,
            )

        counts = {
            name: 0
            for name in VEHICLE_CLASSES.values()
        }

        tracks = []
        occupied_labels = []

        frame_height, frame_width = annotated.shape[:2]

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.45
        thickness = 1
        label_padding = 4

        if not results or results[0].boxes is None:
            return annotated, counts, tracks

        for box in results[0].boxes:

            # Get the detected vehicle class.
            class_id = int(box.cls[0].item())

            if class_id not in VEHICLE_CLASSES:
                continue

            vehicle_name = VEHICLE_CLASSES[class_id]
            color = VEHICLE_COLORS[vehicle_name]

            confidence = float(box.conf[0].item())

            # Get tracking ID when available.
            track_id = None

            if box.id is not None:
                track_id = int(box.id[0].item())

            # Get bounding-box coordinates.
            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0].tolist(),
            )

            # Keep coordinates inside the video frame.
            x1 = max(0, min(x1, frame_width - 1))
            y1 = max(0, min(y1, frame_height - 1))
            x2 = max(0, min(x2, frame_width - 1))
            y2 = max(0, min(y2, frame_height - 1))

            if x2 <= x1 or y2 <= y1:
                continue

            # Count detected vehicles.
            counts[vehicle_name] += 1

            # Save detection and tracking information.
            tracks.append({
                "class": vehicle_name,
                "track_id": track_id,
                "confidence": round(confidence, 3),
                "bbox": [x1, y1, x2, y2],
            })

            # Draw the vehicle bounding box.
            cv2.rectangle(
                annotated,
                (x1, y1),
                (x2, y2),
                color,
                2,
            )

            # Create vehicle label.
            if track_id is not None:
                label = f"{vehicle_name.title()} ID:{track_id}"
            else:
                label = vehicle_name.title()

            (text_width, text_height), baseline = (
                cv2.getTextSize(
                    label,
                    font,
                    font_scale,
                    thickness,
                )
            )

            label_width = min(
                text_width + label_padding * 2,
                frame_width,
            )

            label_height = min(
                text_height + baseline + label_padding * 2,
                frame_height,
            )

            # Candidate positions for the label.
            candidates = [
                (x1, y1 - label_height),
                (x1, y2 + 2),
                (x1, y1 + 2),
                (x2 - label_width, y1 - label_height),
                (x2 - label_width, y2 + 2),
            ]

            chosen = None

            # Try to avoid overlapping existing labels.
            for candidate_x, candidate_y in candidates:

                candidate_x = max(
                    0,
                    min(
                        candidate_x,
                        max(0, frame_width - label_width),
                    ),
                )

                candidate_y = max(
                    0,
                    min(
                        candidate_y,
                        max(0, frame_height - label_height),
                    ),
                )

                rect = (
                    candidate_x,
                    candidate_y,
                    candidate_x + label_width,
                    candidate_y + label_height,
                )

                if not any(
                    _overlaps(rect, existing)
                    for existing in occupied_labels
                ):
                    chosen = rect
                    break

            # Fallback position if all candidate positions overlap.
            if chosen is None:

                candidate_x = max(
                    0,
                    min(
                        x1,
                        max(0, frame_width - label_width),
                    ),
                )

                candidate_y = max(
                    0,
                    min(
                        y1 - label_height,
                        max(0, frame_height - label_height),
                    ),
                )

                chosen = (
                    candidate_x,
                    candidate_y,
                    candidate_x + label_width,
                    candidate_y + label_height,
                )

            occupied_labels.append(chosen)

            lx1, ly1, lx2, ly2 = chosen

            # Draw label background using the vehicle's colour.
            cv2.rectangle(
                annotated,
                (lx1, ly1),
                (
                    min(lx2, frame_width - 1),
                    min(ly2, frame_height - 1),
                ),
                color,
                -1,
            )

            # Draw readable white text.
            text_x = min(
                lx1 + label_padding,
                frame_width - 1,
            )

            text_y = min(
                ly1 + label_padding + text_height,
                frame_height - 1,
            )

            cv2.putText(
                annotated,
                label,
                (text_x, text_y),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

        return annotated, counts, tracks
