# Module 8 — Historical Data and Analytics (Backend)

## Included features
- Save and list traffic/parking observations in SQLAlchemy.
- Filter observations by location or observation type.
- Compare peak and off-peak vehicle counts.
- Rank busy locations and show minimum available parking spaces.
- Evaluate prediction accuracy using MAE, RMSE, and MAPE.
- Export stored observations as a downloadable CSV report.
- Database health endpoint.

## Run locally
From the project root:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows; optional
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the API. If `DATABASE_URL` is not configured,
SQLite is used automatically. For PostgreSQL, configure `DATABASE_URL` in `.env` and
ensure the database exists before starting the server.

## Main endpoints
- `GET /health/db`
- `POST /observations` — JSON body with location, observation_type, vehicle_count,
  available_parking_spaces, optional average_speed_kmh and recorded_at.
- `GET /observations?limit=100&location=...&observation_type=...`
- `GET /analytics/peak-hours`
- `GET /analytics/peak-vs-off-peak?peak_start=7&peak_end=10`
- `GET /analytics/busy-locations`
- `POST /analytics/prediction-accuracy`
- `GET /reports/export`

Prediction accuracy request example:
```json
{"actual_values": [100, 120, 90], "predicted_values": [95, 125, 85]}
```

Notes: peak start is inclusive and peak end is exclusive. For overnight peak windows,
the range wraps across midnight. Analytics use the observations currently stored in
the database; meaningful reports require representative, timestamped sample data.
