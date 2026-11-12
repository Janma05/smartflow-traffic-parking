
import cv2
import time
import numpy as np


def monitor_camera(source=0, checks=8, interval=0.5, threshold=1.0):
    """
    Monitor webcam or video file.
    Detect unavailable cameras, interrupted feeds and frozen frames.
    """

    if checks < 2 or interval < 0 or threshold < 0:
        raise ValueError("Invalid camera monitoring parameters")

    # Convert numeric camera source strings into integers
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        cap.release()
        return {
            "status": "offline",
            "alert_type": "camera_unavailable",
            "message": f"Camera source {source} is unavailable",
            "is_alert": True
        }

    previous_frame = None
    frozen_count = 0
    movement_values = []

    try:
        for _ in range(checks):
            success, frame = cap.read()

            if not success or frame is None:
                return {
                    "status": "offline",
                    "alert_type": "camera_unavailable",
                    "message": "Camera stopped sending video frames",
                    "is_alert": True
                }

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 240))

            if previous_frame is not None:
                difference = cv2.absdiff(previous_frame, gray)
                movement = float(np.mean(difference))
                movement_values.append(round(movement, 3))

                if movement < threshold:
                    frozen_count += 1
                else:
                    frozen_count = 0

            previous_frame = gray
            time.sleep(interval)

        if frozen_count >= checks - 1:
            return {
                "status": "frozen",
                "alert_type": "camera_frozen",
                "message": "Camera feed appears frozen",
                "is_alert": True,
                "movement_values": movement_values
            }

        return {
            "status": "online",
            "alert_type": None,
            "message": "Camera is working normally",
            "is_alert": False,
            "movement_values": movement_values
        }

    finally:
        cap.release()
