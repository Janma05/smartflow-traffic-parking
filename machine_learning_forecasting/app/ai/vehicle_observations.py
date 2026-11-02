
"""Adapter to turn Module 1 traffic summaries into Module 3 historical observations."""
from datetime import datetime
from pathlib import Path
import pandas as pd

def append_observation(csv_path: str, timestamp: str, location_id: str,
                       vehicle_count: int, average_speed: float | None = None) -> dict:
    """Append one interval-level count emitted by Module 1 to the history CSV.

    vehicle_count must be a count for a defined interval (e.g. vehicles passing
    a virtual line in 5 minutes), not average detections per video frame.
    """
    if int(vehicle_count) < 0:
        raise ValueError("vehicle_count must be >= 0")
    pd.to_datetime(timestamp)  # validate timestamp
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": timestamp, "location_id": str(location_id), "vehicle_count": int(vehicle_count)}
    if average_speed is not None:
        row["average_speed"] = float(average_speed)
    new = pd.DataFrame([row])
    if path.exists() and path.stat().st_size:
        old = pd.read_csv(path)
        new = pd.concat([old, new], ignore_index=True)
    new.to_csv(path, index=False)
    return {"status": "saved", "observation": row, "csv_path": str(path)}
