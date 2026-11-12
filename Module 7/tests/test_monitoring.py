import numpy as np
from datetime import datetime, timezone

import app.camera_monitor as camera_module
from app.sensor_monitor import monitor_sensor


# ---------------- CAMERA TESTS ----------------

class FakeCamera:
    def __init__(self, opened=True, frames=None):
        self.opened = opened
        self.frames = frames or []
        self.index = 0
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if self.index < len(self.frames):
            frame = self.frames[self.index]
            self.index += 1
            return True, frame
        return False, None

    def release(self):
        self.released = True


def test_camera_unavailable(monkeypatch):
    fake = FakeCamera(opened=False)
    monkeypatch.setattr(camera_module.cv2, "VideoCapture",
                        lambda source: fake)

    result = camera_module.monitor_camera("missing_camera.mp4")

    assert result["status"] == "offline"
    assert result["alert_type"] == "camera_unavailable"
    assert result["is_alert"] is True
    assert fake.released is True


def test_camera_working(monkeypatch):
    frames = [
        np.full((240, 320, 3), i * 20, dtype=np.uint8)
        for i in range(8)
    ]
    fake = FakeCamera(frames=frames)

    monkeypatch.setattr(camera_module.cv2, "VideoCapture",
                        lambda source: fake)
    monkeypatch.setattr(camera_module.time, "sleep",
                        lambda seconds: None)

    result = camera_module.monitor_camera(
        source=0, checks=8, interval=0
    )

    assert result["status"] == "online"
    assert result["is_alert"] is False


def test_camera_frozen(monkeypatch):
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    fake = FakeCamera(frames=[frame.copy() for _ in range(8)])

    monkeypatch.setattr(camera_module.cv2, "VideoCapture",
                        lambda source: fake)
    monkeypatch.setattr(camera_module.time, "sleep",
                        lambda seconds: None)

    result = camera_module.monitor_camera(
        source=0, checks=8, interval=0
    )

    assert result["status"] == "frozen"
    assert result["alert_type"] == "camera_frozen"
    assert result["is_alert"] is True


# ---------------- SENSOR TESTS ----------------

def test_sensor_offline():
    sensor = {
        "id": "SEN-TEST",
        "is_online": False,
        "last_seen": None
    }

    result = monitor_sensor(sensor)

    assert result["status"] == "offline"
    assert result["alert_type"] == "sensor_failure"
    assert result["is_alert"] is True


def test_sensor_unknown():
    sensor = {
        "id": "SEN-TEST",
        "is_online": True,
        "last_seen": None
    }

    result = monitor_sensor(sensor)

    assert result["status"] == "unknown"
    assert result["is_alert"] is True


def test_sensor_stale():
    sensor = {
        "id": "SEN-TEST",
        "is_online": True,
        "last_seen": "2020-01-01T00:00:00+00:00"
    }

    result = monitor_sensor(sensor)

    assert result["status"] == "stale"
    assert result["alert_type"] == "sensor_failure"
    assert result["is_alert"] is True


def test_sensor_healthy():
    sensor = {
        "id": "SEN-TEST",
        "is_online": True,
        "last_seen": datetime.now(timezone.utc).isoformat()
    }

    result = monitor_sensor(sensor)

    assert result["status"] == "online"
    assert result["is_alert"] is False
