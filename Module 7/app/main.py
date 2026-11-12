
import json
import os
import time
import uuid
import smtplib

from pathlib import Path
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Optional, Literal

import cv2
import numpy as np

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.camera_monitor import monitor_camera
from app.sensor_monitor import monitor_sensor


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "demo_data.json"

PARKING_THRESHOLD = int(os.getenv("PARKING_FULL_THRESHOLD", "90"))
CONGESTION_THRESHOLD = int(os.getenv("SEVERE_CONGESTION_THRESHOLD", "80"))
STALE_SECONDS = int(os.getenv("DEVICE_STALE_SECONDS", "120"))
DEMO = os.getenv("TRAFFIQ_DEMO_MODE", "true").lower() == "true"

app = FastAPI(
    title="TraffiQ / SmartFlow - Module 7 Alerts & Notifications",
    version="1.1.0",
    description="Traffic, parking, camera and sensor monitoring with alerts."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# COMMON FUNCTIONS
# --------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()


def read():
    with DATA.open(encoding="utf-8") as file:
        return json.load(file)


def save(data):
    with DATA.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def alert(data, kind, severity, title, message, sid, sname, meta=None):
    for existing in data["alerts"]:
        if (
            existing["source_id"] == sid
            and existing["alert_type"] == kind
            and existing["status"] == "active"
        ):
            existing.update(
                message=message,
                updated_at=now(),
                metadata=meta or existing.get("metadata", {})
            )
            return existing

    new_alert = {
        "alert_id": str(uuid.uuid4()),
        "alert_type": kind,
        "severity": severity,
        "title": title,
        "message": message,
        "source_id": sid,
        "source_name": sname,
        "status": "active",
        "created_at": now(),
        "updated_at": now(),
        "acknowledged_at": None,
        "metadata": meta or {}
    }

    data["alerts"].insert(0, new_alert)
    return new_alert


# --------------------------------------------------
# EXISTING PARKING MONITORING
# --------------------------------------------------

def check_parking(data):
    results = []

    for parking in data["parking_facilities"]:
        total = int(parking["total_spaces"])
        occupied = int(parking["occupied_spaces"])

        percentage = occupied / total * 100 if total else 0
        parking["occupancy_percent"] = round(percentage, 1)

        if percentage >= PARKING_THRESHOLD:
            results.append(
                alert(
                    data,
                    "parking_nearly_full",
                    "critical" if percentage >= 97 else "warning",
                    f"Parking nearly full: {parking['name']}",
                    f"{parking['name']} is {percentage:.1f}% occupied.",
                    parking["parking_id"],
                    parking["name"],
                    {
                        "occupancy_percent": round(percentage, 1),
                        "available_spaces": max(total - occupied, 0),
                        "threshold_percent": PARKING_THRESHOLD
                    }
                )
            )

    return results


# --------------------------------------------------
# EXISTING ROAD MONITORING
# --------------------------------------------------

def check_roads(data):
    results = []

    for road in data["roads"]:
        score = int(road.get("congestion_score", 0))
        level = str(road.get("congestion_level", "")).lower()

        if score >= CONGESTION_THRESHOLD or level in ("severe", "critical"):
            results.append(
                alert(
                    data,
                    "severe_congestion",
                    "critical" if score >= 90 or level in ("severe", "critical") else "warning",
                    f"Severe congestion: {road['road_name']}",
                    f"{road['road_name']} has {level} congestion (score {score}/100).",
                    road["road_id"],
                    road["road_name"],
                    {
                        "congestion_score": score,
                        "congestion_level": level
                    }
                )
            )

    return results


# --------------------------------------------------
# EXISTING DEVICE STATUS MONITORING
# --------------------------------------------------

def check_devices(data):
    results = []
    current = time.time()

    for group, label, kind in [
        ("cameras", "camera", "camera_unavailable"),
        ("sensors", "sensor", "sensor_failure")
    ]:
        for device in data[group]:
            last_seen = device.get("last_seen_epoch")
            offline = not device.get("is_online", False)

            stale = (
                last_seen is None
                or current - float(last_seen) > STALE_SECONDS
            )

            if offline or stale:
                state = "offline" if offline else "stale"

                results.append(
                    alert(
                        data,
                        kind,
                        "critical" if offline else "warning",
                        f"{label.title()} unavailable: {device['name']}",
                        f"{device['name']} is {state}.",
                        device["device_id"],
                        device["name"],
                        {
                            "device_type": label,
                            "device_status": state,
                            "last_seen": device.get("last_seen"),
                            "stale_after_seconds": STALE_SECONDS
                        }
                    )
                )

    return results


def monitor(data):
    found = (
        check_parking(data)
        + check_roads(data)
        + check_devices(data)
    )

    data["last_monitoring_run"] = now()
    save(data)

    return {
        "monitoring_run_at": data["last_monitoring_run"],
        "alerts_created_or_updated": len(found),
        "alerts": found,
        "demo_data": DEMO
    }


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ParkingUpdate(BaseModel):
    occupied_spaces: int = Field(ge=0)


class RoadUpdate(BaseModel):
    congestion_score: int = Field(ge=0, le=100)
    congestion_level: Literal[
        "low", "medium", "high", "severe", "critical"
    ]


class Heartbeat(BaseModel):
    is_online: bool = True
    status_message: Optional[str] = None


class Ack(BaseModel):
    acknowledged_by: str = Field(min_length=1, max_length=120)


class Notification(BaseModel):
    channel: Literal["email", "push"]
    recipient: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)


# --------------------------------------------------
# HOME AND HEALTH
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "project": "SmartFlow / TraffiQ",
        "module": 7,
        "name": "Alerts and Notifications",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "ok", "module": 7}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


# --------------------------------------------------
# ALERT APIs
# --------------------------------------------------

@app.get("/api/v1/alerts")
def list_alerts(
    status: Optional[Literal["active", "acknowledged", "resolved"]] = None,
    severity: Optional[Literal["info", "warning", "critical"]] = None,
    alert_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    items = read()["alerts"]

    if status:
        items = [a for a in items if a["status"] == status]

    if severity:
        items = [a for a in items if a["severity"] == severity]

    if alert_type:
        items = [a for a in items if a["alert_type"] == alert_type]

    return {"count": len(items[:limit]), "alerts": items[:limit]}


@app.get("/api/v1/alerts/summary")
def summary():
    items = read()["alerts"]

    return {
        "total": len(items),
        "active": sum(a["status"] == "active" for a in items),
        "acknowledged": sum(a["status"] == "acknowledged" for a in items),
        "critical": sum(
            a["severity"] == "critical" and a["status"] == "active"
            for a in items
        ),
        "warning": sum(
            a["severity"] == "warning" and a["status"] == "active"
            for a in items
        )
    }


@app.post("/api/v1/monitoring/run")
def run_monitoring():
    return monitor(read())


# --------------------------------------------------
# PARKING APIs
# --------------------------------------------------

@app.get("/api/v1/parking")
def parking():
    data = read()
    results = []

    for p in data["parking_facilities"]:
        item = dict(p)
        total = item["total_spaces"]
        occupied = item["occupied_spaces"]

        item["available_spaces"] = max(total - occupied, 0)
        item["occupancy_percent"] = round(
            occupied / total * 100, 1
        ) if total else 0

        results.append(item)

    return {"parking_facilities": results}


@app.put("/api/v1/parking/{parking_id}")
def update_parking(parking_id: str, body: ParkingUpdate):
    data = read()

    parking = next(
        (p for p in data["parking_facilities"]
         if p["parking_id"] == parking_id),
        None
    )

    if not parking:
        raise HTTPException(404, "Parking facility not found")

    if body.occupied_spaces > parking["total_spaces"]:
        raise HTTPException(422, "Occupied spaces cannot exceed total spaces")

    parking["occupied_spaces"] = body.occupied_spaces
    parking["updated_at"] = now()

    check_parking(data)
    save(data)

    return {"message": "Parking updated", "parking": parking}


# --------------------------------------------------
# ROAD APIs
# --------------------------------------------------

@app.get("/api/v1/roads")
def roads():
    return {"roads": read()["roads"]}


@app.put("/api/v1/roads/{road_id}")
def update_road(road_id: str, body: RoadUpdate):
    data = read()

    road = next(
        (r for r in data["roads"] if r["road_id"] == road_id),
        None
    )

    if not road:
        raise HTTPException(404, "Road not found")

    road.update(
        congestion_score=body.congestion_score,
        congestion_level=body.congestion_level,
        observed_at=now()
    )

    check_roads(data)
    save(data)

    return {"message": "Road updated", "road": road}


# --------------------------------------------------
# DEVICE APIs
# --------------------------------------------------

@app.get("/api/v1/devices")
def devices():
    data = read()
    return {
        "cameras": data["cameras"],
        "sensors": data["sensors"]
    }


@app.post("/api/v1/devices/{device_id}/heartbeat")
def heartbeat(device_id: str, body: Heartbeat):
    data = read()
    device = None

    for group in ("cameras", "sensors"):
        device = next(
            (x for x in data[group] if x["device_id"] == device_id),
            None
        )
        if device:
            break

    if not device:
        raise HTTPException(404, "Camera or sensor not found")

    device.update(
        is_online=body.is_online,
        last_seen_epoch=time.time(),
        last_seen=now(),
        status_message=body.status_message
    )

    save(data)
    return {"message": "Heartbeat recorded", "device": device}


# --------------------------------------------------
# OPENCV CAMERA MONITORING API
# --------------------------------------------------

@app.post("/api/v1/devices/{device_id}/camera-check")
def camera_check(
    device_id: str,
    source: str = Query(
        "0",
        description="Webcam index or video file path"
    )
):
    data = read()

    device = next(
        (x for x in data["cameras"] if x["device_id"] == device_id),
        None
    )

    if not device:
        raise HTTPException(404, "Camera not found")

    # Use webcam index 0, or provide a video file path.
    camera_source = int(source) if source.isdigit() else source

    try:
        result = monitor_camera(source=camera_source)
    except Exception as exc:
        raise HTTPException(
            500,
            f"Camera monitoring failed: {type(exc).__name__}"
        ) from exc

    device["is_online"] = not result["is_alert"]
    device["last_seen_epoch"] = time.time()
    device["last_seen"] = now()
    device["status_message"] = result["message"]

    if result["is_alert"]:
        alert(
            data,
            result["alert_type"],
            "critical",
            f"Camera failure: {device['name']}",
            result["message"],
            device_id,
            device["name"],
            {"detection_method": "OpenCV", "camera_status": result["status"]}
        )

    save(data)

    return {
        "device_id": device_id,
        "camera_result": result
    }


# --------------------------------------------------
# SENSOR MONITORING API
# --------------------------------------------------

@app.post("/api/v1/devices/{device_id}/sensor-check")
def sensor_check(device_id: str):
    data = read()

    device = next(
        (x for x in data["sensors"] if x["device_id"] == device_id),
        None
    )

    if not device:
        raise HTTPException(404, "Sensor not found")

    result = monitor_sensor(device, STALE_SECONDS)

    if result["is_alert"]:
        alert(
            data,
            "sensor_failure",
            "critical",
            f"Sensor failure: {device['name']}",
            result["message"],
            device_id,
            device["name"],
            {"detection_method": "Heartbeat", "sensor_status": result["status"]}
        )

    save(data)

    return {
        "device_id": device_id,
        "sensor_result": result
    }


# --------------------------------------------------
# ACKNOWLEDGE AND RESOLVE ALERTS
# --------------------------------------------------

@app.post("/api/v1/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: str, body: Ack):
    data = read()

    item = next(
        (a for a in data["alerts"] if a["alert_id"] == alert_id),
        None
    )

    if not item:
        raise HTTPException(404, "Alert not found")

    if item["status"] == "resolved":
        raise HTTPException(409, "Resolved alert cannot be acknowledged")

    item.update(
        status="acknowledged",
        acknowledged_by=body.acknowledged_by,
        acknowledged_at=now(),
        updated_at=now()
    )

    save(data)
    return {"message": "Alert acknowledged", "alert": item}


@app.post("/api/v1/alerts/{alert_id}/resolve")
def resolve(alert_id: str):
    data = read()

    item = next(
        (a for a in data["alerts"] if a["alert_id"] == alert_id),
        None
    )

    if not item:
        raise HTTPException(404, "Alert not found")

    item.update(
        status="resolved",
        resolved_at=now(),
        updated_at=now()
    )

    save(data)
    return {"message": "Alert resolved", "alert": item}


# --------------------------------------------------
# EMAIL NOTIFICATION
# --------------------------------------------------

def email_send(to, subject, body):
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user or "")

    if not all([host, user, password, sender]):
        raise HTTPException(503, "SMTP is not configured")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content(body)

    try:
        with smtplib.SMTP(
            host, int(os.getenv("SMTP_PORT", "587")), timeout=15
        ) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)

    except (smtplib.SMTPException, OSError) as exc:
        raise HTTPException(502, "Email delivery failed") from exc

    return {"channel": "email", "status": "sent", "recipient": to}


# --------------------------------------------------
# PUSH NOTIFICATION
# --------------------------------------------------

def fcm_send(token, title, body):
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError as exc:
        raise HTTPException(
            503, "Install firebase-admin to use push notifications"
        ) from exc

    if not firebase_admin._apps:
        path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not path or not Path(path).exists():
            raise HTTPException(503, "Firebase credentials not configured")

        firebase_admin.initialize_app(
            credentials.Certificate(path)
        )

    try:
        message_id = messaging.send(
            messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                token=token
            )
        )
    except Exception as exc:
        raise HTTPException(502, "Push notification failed") from exc

    return {
        "channel": "push",
        "status": "sent",
        "message_id": message_id
    }


@app.post("/api/v1/notifications/send")
def send_notification(body: Notification):
    if body.channel == "email":
        return email_send(
            body.recipient, body.title, body.message
        )

    return fcm_send(
        body.recipient, body.title, body.message
    )


# --------------------------------------------------
# CONFIGURATION API
# --------------------------------------------------

@app.get("/api/v1/config")
def config():
    return {
        "parking_threshold_percent": PARKING_THRESHOLD,
        "congestion_threshold": CONGESTION_THRESHOLD,
        "device_stale_seconds": STALE_SECONDS,
        "demo_mode": DEMO,
        "email_configured": bool(
            os.getenv("SMTP_HOST") and os.getenv("SMTP_USERNAME")
        ),
        "push_configured": bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        ),
        "opencv_available": True
    }
