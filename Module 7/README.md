# TraffiQ / SmartFlow Module 7 — Alerts and Notifications

FastAPI backend demo for parking occupancy alerts, severe congestion alerts, camera/sensor offline or stale detection, dashboard alert management, optional SMTP email and Firebase Cloud Messaging (FCM).

## Run (Windows / VS Code)
1. Extract ZIP and open folder in VS Code.
2. Terminal → New Terminal.
3. `py -m venv .venv`
4. ` .\.venv\Scripts\Activate.ps1` (if blocked, use `.venv\Scripts\python.exe` directly).
5. `python -m pip install --upgrade pip` then `pip install -r requirements.txt`
6. `python -m uvicorn app.main:app --reload`
7. Open http://127.0.0.1:8000/docs

## Demo sequence
- GET `/api/v1/parking`, `/roads`, `/devices` show dummy data.
- POST `/api/v1/monitoring/run` creates/updates alerts from the sample data.
- GET `/api/v1/alerts` and `/api/v1/alerts/summary`.
- Acknowledge: POST `/api/v1/alerts/{alert_id}/acknowledge` body `{"acknowledged_by":"Admin"}`. Resolve: POST `/api/v1/alerts/{alert_id}/resolve`.
- Parking update: PUT `/api/v1/parking/PARK-002` body `{"occupied_spaces":145}`. Road update: PUT `/api/v1/roads/ROAD-102` body `{"congestion_score":95,"congestion_level":"severe"}`.
- Heartbeat: POST `/api/v1/devices/CAM-002/heartbeat` body `{"is_online":true,"status_message":"Restored"}`.

## Rules
Parking alert at >=90% occupancy; congestion at score >=80 or level severe/critical; devices stale after 120 seconds or immediately offline. Thresholds are environment-configurable.

## Email and push
Email and FCM are real integrations and require credentials. Email: set SMTP_HOST/PORT/USERNAME/PASSWORD/FROM. Gmail generally requires an App Password. FCM: install `pip install firebase-admin`, set GOOGLE_APPLICATION_CREDENTIALS to Firebase service-account JSON. Do not commit credentials. If not configured, endpoints return 503 rather than pretending delivery.

## Limitations
Sample data is synthetic, not live traffic/cameras/sensors. Monitoring runs when endpoint is called; production should schedule it or trigger from events. Demo data uses JSON storage; production should use PostgreSQL.
