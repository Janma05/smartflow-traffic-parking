# Module 5 — Frontend Integration Contract

Base URL for local development: `http://127.0.0.1:8000`

Swagger docs: `http://127.0.0.1:8000/docs`

CORS is configured for local React origins `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, and `http://127.0.0.1:5173`.

## 1) Main endpoint — recommend and compare routes

`POST /api/v1/routes/recommend`

Request schema:

```json
{
  "origin": "Vijayanagar, Bengaluru",
  "destination": "MG Road, Bengaluru",
  "traffic_aware": true,
  "use_sample_data": true
}
```

- `origin` / `destination`: strings. In sample mode these are display labels.
- `traffic_aware`: apply the supplied synthetic traffic factors in sample mode.
- `use_sample_data`: `true` uses deterministic sample data; `false` invokes OSRM and requires coordinate strings in `longitude,latitude` format. If omitted, server default mode is used.

Response shape (values abbreviated):

```json
{
  "request": {
    "origin": "Vijayanagar, Bengaluru",
    "destination": "MG Road, Bengaluru",
    "traffic_aware": true,
    "use_sample_data": true
  },
  "provider": "TraffiQ synthetic demo dataset",
  "is_demo_data": true,
  "live_traffic_available": false,
  "routes": [
    {
      "route_id": "R2",
      "name": "Route B - Outer Connector",
      "distance_km": 10.1,
      "base_duration_min": 23.0,
      "traffic_factor": 1.08,
      "congestion_level": "low",
      "congestion_score": 24,
      "estimated_duration_min": 24.8,
      "traffic_delay_min": 1.8,
      "traffic_aware": true,
      "rank": 1,
      "recommended": true,
      "recommendation_reason": "Lowest estimated travel time among the available candidates.",
      "geometry": {"type": "LineString", "coordinates": [[77.532, 12.971], [77.558, 12.953]]}
    }
  ],
  "recommended_route": {},
  "notice": "Synthetic sample data only..."
}
```

The route list is sorted by `estimated_duration_min`. Use `recommended === true` to highlight the recommended route. `geometry` is GeoJSON `LineString` and can be passed to Leaflet after coordinate-order handling.

## 2) Sample route endpoint

`GET /api/v1/routes/sample?origin=Vijayanagar,%20Bengaluru&destination=MG%20Road,%20Bengaluru&traffic_aware=true`

Use this for a quick read-only demo. It returns `summary` plus a `routes` array.

## 3) Traffic status feed (placeholder for Module 1)

`GET /api/v1/traffic/road-status`

Response includes:
- `observations[]`
- `road_id`
- `road_name`
- `congestion_level` (`low`, `medium`, `high`)
- `congestion_score` (0–100)
- `average_speed_kmph`
- `vehicle_count_5min`
- `observed_at` (ISO timestamp)

This is synthetic example data. Coordinate with the Module 1 owner to replace it with their actual schema and identify how road segments map to candidate routes.

## 4) Suggested frontend behavior
- Form fields: origin and destination.
- Submit to `POST /api/v1/routes/recommend`.
- Render each route as a card with distance, estimated duration, congestion, delay and rank.
- Highlight the route with `recommended: true`.
- If `is_demo_data` is true, display a visible “Demo / sample data” badge.
- Display the `notice` field in a small disclaimer.
- For a map, draw each route's GeoJSON geometry using Leaflet. Sample geometries are illustrative only; don't represent them as verified driving directions.
- Show loading and error states (422 validation, 502 provider unavailable, 504 timeout).

## 5) Integration questions for the team
Before replacing synthetic values, agree with Module 1 on:
1. API endpoint or event source for traffic observations.
2. Road/segment IDs and how routes map to road segments.
3. Observation timestamps and maximum acceptable data age.
4. Congestion score definitions and thresholds.
5. Whether route ETA should use a provider's traffic-aware ETA or an internally computed delay model.
