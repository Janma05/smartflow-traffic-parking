# Module 7 Frontend Handoff
Base URL `http://127.0.0.1:8000`; Swagger `/docs`. CORS supports localhost React ports 3000 and 5173.

Dashboard: GET `/api/v1/alerts?status=active&severity=critical`; GET `/api/v1/alerts/summary`; POST `/api/v1/monitoring/run`; POST `/api/v1/alerts/{alert_id}/acknowledge` body `{"acknowledged_by":"Admin"}`; POST `/api/v1/alerts/{alert_id}/resolve`.

Inputs: GET `/api/v1/parking`, `/roads`, `/devices`; PUT `/api/v1/parking/{parking_id}` body `{"occupied_spaces":145}`; PUT `/api/v1/roads/{road_id}` body `{"congestion_score":95,"congestion_level":"severe"}`; POST `/api/v1/devices/{device_id}/heartbeat` body `{"is_online":true,"status_message":"Camera OK"}`.

Notifications: POST `/api/v1/notifications/send`. Email JSON: `{"channel":"email","recipient":"admin@example.com","title":"Congestion","message":"Road alert"}`. Push JSON: `{"channel":"push","recipient":"FCM_DEVICE_TOKEN","title":"Parking full","message":"Parking nearly full"}`. These require backend credentials.

Alert fields: alert_id, alert_type, severity, title, message, source_id, source_name, status, created_at, updated_at, acknowledged_at, metadata. Show severity/status badges and clearly label sample data as demo.
