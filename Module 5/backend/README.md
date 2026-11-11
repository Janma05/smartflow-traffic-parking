# TraffiQ / SmartFlow — Module 5: Route Recommendation

A demo-ready FastAPI backend for route comparison and recommendation. It includes a deterministic synthetic dataset so the demo works without external routing APIs.

## Features in this package
- Compare multiple candidate routes.
- Estimate travel time using synthetic traffic factors.
- Recommend an alternative when the direct route has high congestion.
- Sample traffic status endpoint designed for integration with Module 1.
- Optional OSRM route mode for road distance, route geometry, and base duration.
- CORS enabled for local React development on ports 3000 and 5173.
- Swagger API docs and sample requests for frontend handoff.

## Requirements
- Python 3.10+
- VS Code
- Internet is NOT required for demo mode.
- Internet IS required for OSRM mode.

## Windows / VS Code setup
1. Extract the ZIP.
2. In VS Code, select File → Open Folder and open `TraffiQ_Module5_Demo`.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

5. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, skip activation and use `.venv\Scripts\python.exe` in the commands below.

6. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Run the API:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

8. Open:
   - API docs: http://127.0.0.1:8000/docs
   - Home: http://127.0.0.1:8000
   - Health: http://127.0.0.1:8000/health

Demo mode is enabled by default (`TRAFFIQ_DEMO_MODE=true`) and does not require a database or external service.

## Demo walkthrough (recommended)
1. Open `http://127.0.0.1:8000/docs`.
2. Expand `GET /api/v1/routes/sample`.
3. Click Try it out, use the default origin/destination, keep `traffic_aware=true`, then Execute.
4. Show the routes: Route A has high congestion and a larger delay; Route B is likely to be ranked first because its estimated time is lower.
5. Expand `POST /api/v1/routes/recommend`, click Try it out, and use:

   ```json
   {
     "origin": "Vijayanagar, Bengaluru",
     "destination": "MG Road, Bengaluru",
     "traffic_aware": true,
     "use_sample_data": true
   }
   ```

6. Compare by setting `"traffic_aware": false`. With traffic adjustment disabled, the ranking may change because the base durations are compared instead.
7. Show `GET /api/v1/traffic/road-status` to explain the expected shape of traffic data from Module 1.

All sample locations, scores, vehicle counts, route distances, and times are synthetic and are for demonstration only. Do not present them as live Bengaluru traffic.

## Optional OSRM mode
The standard public OSRM service provides route geometry, distance, and estimated base duration, but not live traffic. To try OSRM through `POST /api/v1/routes/recommend`, send coordinate strings:

```json
{
  "origin": "77.5946,12.9716",
  "destination": "77.6101,12.9352",
  "traffic_aware": false,
  "use_sample_data": false
}
```

Coordinate string order is `longitude,latitude`. OSRM mode requires internet access and does not geocode street addresses. The public OSRM demo has usage limits.

## Frontend team handoff
See `docs/FRONTEND_HANDOFF.md` for API contracts, response examples, CORS, and integration notes.

## Current limitations / integration work remaining
- Sample traffic factors are synthetic, not live camera detections.
- `GET /api/v1/traffic/road-status` is a placeholder feed. Replace it with the agreed Module 1 API/schema.
- Route geometries in the sample data are illustrative line coordinates, not verified navigation roads.
- OSRM mode gives base route alternatives but not traffic-aware travel time.
- No geocoding, database persistence, authentication, or production deployment is included.
- Before production, agree on data freshness, route-to-road segment matching, error handling, provider terms, and CORS origins.
