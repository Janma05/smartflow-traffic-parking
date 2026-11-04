
# SmartFlow Module 3 — Complete Starter Implementation

Implements the Module 3 scope from the SmartFlow project brief:
- historical traffic analysis
- peak-hour and recurring day/hour pattern analysis
- next-interval vehicle-volume prediction with Random Forest regression
- congestion category estimation from dataset-derived thresholds
- optional Random Forest congestion classifier when there is sufficient data
- FastAPI endpoints to save observations, analyze, train, and predict
- adapter to accept timestamped vehicle counts from Module 1

## CSV schema
Required: `timestamp`, `vehicle_count`.
Recommended: `location_id`; optional: `average_speed`.
Example:
```csv
timestamp,location_id,vehicle_count,average_speed
2026-10-01 08:00:00,Road-A,14,22.5
2026-10-01 09:00:00,Road-A,28,15.2
```
`data/traffic_history.csv` is SYNTHETIC demo data only. Replace with real observations before reporting results.

## Windows setup
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.api:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Swagger workflow
1. `GET /prediction/analyze`
2. `POST /prediction/train`, body `{}`.
3. `POST /prediction/predict`, body `{"location_id":"default"}`.
4. `POST /prediction/observations` to append a new interval observation:
```json
{"timestamp":"2026-10-29T10:00:00","location_id":"Road-A","vehicle_count":21,"average_speed":24.5}
```
Use a location that has enough history before training/predicting.

## What Module 1 must provide
Module 1 should emit counts by consistent intervals and locations, ideally every 5/15/60 minutes. A video summary's average vehicles per frame is not equivalent to vehicles passing a road in an hour. For meaningful forecasting, use line-crossing counts or another consistent interval count, timestamp each observation, and store it.

## Integrating into existing SmartFlow backend
This is a self-contained starter package. Before merging, inspect the existing project structure and merge the endpoint definitions into the existing FastAPI `main.py`/router pattern rather than replacing existing app startup, database setup, authentication, or other modules. The current package writes CSV for a simple prototype; production integration should use the team's PostgreSQL observation table.

## Modelling cautions
- The model is a baseline, not a production-grade forecasting system.
- Evaluation is chronological (earlier observations train, later observations test). MAE/RMSE are error metrics, not accuracy percentages.
- Congestion thresholds are estimated from the dataset's 33rd and 67th percentiles; agree on location-specific thresholds with the project team.
- More representative history and features (weather, incidents, holidays, road work, speed, upstream counts) can improve forecasting.
- Don't claim real-world performance from synthetic demo data.
