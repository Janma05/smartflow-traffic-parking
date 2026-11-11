"""YOLO vehicle detector adapted to the backend's rectangular parking-space model.

Vehicle classes use the COCO IDs: car=2, motorcycle=3, bus=5, truck=7.
A bay is occupied when a vehicle box overlaps at least 25% of its area,
or the vehicle-box centre falls inside the bay.
"""
from __future__ import annotations

import os
from typing import Sequence

import cv2
import numpy as np

from app.detector import BaseDetector, DetectionResult, SpaceRegion
from app.models import STATUS_OCCUPIED, STATUS_VACANT

VEHICLE_CLASSES = {2, 3, 5, 7}


class YoloParkingDetector(BaseDetector):
    name = "yolov8"

    def __init__(self, model_path: str | None = None, confidence: float = 0.25,
                 overlap_threshold: float = 0.25):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "YOLO dependencies are missing. From the project root run: "
                "pip install -r backend/requirements.txt && "
                "pip install -r backend/ai/requirements.txt"
            ) from exc
        self.model_path = model_path or os.getenv("YOLO_MODEL", "yolov8n.pt")
        self.model = YOLO(self.model_path)
        self.confidence = confidence
        self.overlap_threshold = overlap_threshold

    def detect(self, image: np.ndarray,
               regions: Sequence[SpaceRegion]) -> list[DetectionResult]:
        height, width = image.shape[:2]
        prediction = self.model.predict(image, conf=self.confidence, verbose=False)[0]
        vehicle_boxes = []
        if prediction.boxes is not None:
            for box in prediction.boxes:
                class_id = int(box.cls[0].item())
                if class_id not in VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width, x2), min(height, y2)
                if x2 > x1 and y2 > y1:
                    vehicle_boxes.append((x1, y1, x2, y2))

        results = []
        for region in regions:
            x1, y1 = max(0, region.x), max(0, region.y)
            x2 = min(width, region.x + region.width)
            y2 = min(height, region.y + region.height)
            if x2 <= x1 or y2 <= y1:
                results.append(DetectionResult(
                    region.id, None, None,
                    "Parking-space rectangle is outside the image; skipped."
                ))
                continue
            area = max(region.width * region.height, 1)
            best_overlap = 0.0
            occupied = False
            for bx1, by1, bx2, by2 in vehicle_boxes:
                ix1, iy1 = max(x1, bx1), max(y1, by1)
                ix2, iy2 = min(x2, bx2), min(y2, by2)
                intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                box_area = max((bx2 - bx1) * (by2 - by1), 1)
                overlap = intersection / box_area
                best_overlap = max(best_overlap, overlap)
                center_x, center_y = (bx1 + bx2) / 2, (by1 + by2) / 2
                if overlap >= self.overlap_threshold or (
                    x1 <= center_x <= x2 and y1 <= center_y <= y2
                ):
                    occupied = True
            score = round(best_overlap, 4)
            results.append(DetectionResult(
                region.id,
                STATUS_OCCUPIED if occupied else STATUS_VACANT,
                score
            ))
        return results


def draw_vehicle_boxes(image: np.ndarray, detector: YoloParkingDetector) -> np.ndarray:
    """Optional utility reserved for AI-specific overlays."""
    return image.copy()
