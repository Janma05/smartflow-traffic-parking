
from ultralytics import YOLO

# Required vehicle classes from the COCO dataset
VEHICLE_CLASSES = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


class VehicleDetector:
    def __init__(self, model_path="yolo11n.pt"):
        """Load the YOLO model."""
        self.model = YOLO(model_path)

    def process_frame(self, frame):
        """Detect and track the required vehicle classes."""

        result = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=list(VEHICLE_CLASSES.keys()),
            conf=0.15,
            verbose=False,
        )[0]

        # Initialize counts for every vehicle category
        counts = {
            name: 0 for name in VEHICLE_CLASSES.values()
        }

        tracks = []

        # Process detected vehicles
        for box in result.boxes:
            class_id = int(box.cls[0].item())

            # Ignore unwanted classes
            if class_id not in VEHICLE_CLASSES:
                continue

            vehicle_name = VEHICLE_CLASSES[class_id]
            counts[vehicle_name] += 1

            # Get tracking ID when available
            track_id = (
                int(box.id[0].item())
                if box.id is not None
                else None
            )

            confidence = float(box.conf[0].item())

            tracks.append({
                "class": vehicle_name,
                "track_id": track_id,
                "confidence": round(confidence, 3),
            })

        # Draw bounding boxes and labels
        annotated_frame = result.plot()

        return annotated_frame, counts, tracks
