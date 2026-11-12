from datetime import datetime, timezone


def monitor_sensor(sensor, stale_seconds=120):
    if not sensor.get("is_online", False):
        return {
            "status": "offline",
            "alert_type": "sensor_failure",
            "message": "Sensor is offline",
            "is_alert": True
        }

    last_seen = sensor.get("last_seen")

    if not last_seen:
        return {
            "status": "unknown",
            "alert_type": "sensor_failure",
            "message": "Sensor heartbeat is missing",
            "is_alert": True
        }

    try:
        timestamp = datetime.fromisoformat(
            last_seen.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        age = (datetime.now(timezone.utc) - timestamp).total_seconds()

        if age > stale_seconds:
            return {
                "status": "stale",
                "alert_type": "sensor_failure",
                "message": "Sensor heartbeat is overdue",
                "is_alert": True
            }

        return {
            "status": "online",
            "alert_type": None,
            "message": "Sensor is working normally",
            "is_alert": False
        }

    except (ValueError, TypeError, AttributeError):
        return {
            "status": "unknown",
            "alert_type": "sensor_failure",
            "message": "Invalid heartbeat timestamp",
            "is_alert": True
        }
