import json
import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEMO_MODE = os.getenv("TRAFFIQ_DEMO_MODE", "true").lower() == "true"
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")

app = FastAPI(
    title="TraffiQ / SmartFlow - Module 5 Route Recommendation",
    description=(
        "Route comparison and recommendation API. Demo mode uses clearly labelled "
        "synthetic sample data; OSRM mode retrieves road routes but does not provide live traffic."
    ),
    version="1.0.0",
)

# Allow local React development servers. Restrict origins appropriately before production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RouteRequest(BaseModel):
    origin: str = Field(..., min_length=2, description="Human-readable origin name")
    destination: str = Field(..., min_length=2, description="Human-readable destination name")
    traffic_aware: bool = True
    use_sample_data: Optional[bool] = None


def load_sample_data():
    with open(DATA_DIR / "sample_routes.json", "r", encoding="utf-8") as f:
        return json.load(f)


def congestion_rank(level: str) -> int:
    return {"low": 1, "medium": 2, "high": 3, "severe": 4}.get(level.lower(), 2)


def score_route(route: dict, traffic_aware: bool = True) -> float:
    """Lower is better. Sample/observed traffic delay is applied only when traffic-aware."""
    base = float(route["base_duration_min"])
    factor = float(route.get("traffic_factor", 1.0)) if traffic_aware else 1.0
    return base * factor


def rank_routes(routes: list, traffic_aware: bool = True) -> list:
    enriched = []
    for raw in routes:
        route = dict(raw)
        route["estimated_duration_min"] = round(score_route(route, traffic_aware), 1)
        route["traffic_aware"] = traffic_aware
        route["traffic_delay_min"] = round(
            max(0, route["estimated_duration_min"] - float(route["base_duration_min"])), 1
        )
        enriched.append(route)

    enriched.sort(key=lambda r: (r["estimated_duration_min"], r["distance_km"]))
    for idx, route in enumerate(enriched, start=1):
        route["rank"] = idx
        route["recommended"] = idx == 1
        route["recommendation_reason"] = (
            "Lowest estimated travel time among the available candidates."
            if idx == 1
            else "Alternative route; compare time, distance, and congestion."
        )
    return enriched


@app.get("/")
def home():
    return {
        "project": "TraffiQ / SmartFlow",
        "module": 5,
        "name": "Route Recommendation",
        "status": "running",
        "mode": "demo_sample_data" if DEMO_MODE else "osrm",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "demo_sample_data" if DEMO_MODE else "osrm",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/v1/routes/sample")
def sample_routes(
    origin: str = Query(default="Vijayanagar, Bengaluru"),
    destination: str = Query(default="MG Road, Bengaluru"),
    traffic_aware: bool = True,
):
    """Return deterministic sample routes for a reliable offline demo."""
    data = load_sample_data()
    candidates = data["demo_routes"]
    ranked = rank_routes(candidates, traffic_aware=traffic_aware)
    return {
        "request": {
            "origin": origin,
            "destination": destination,
            "traffic_aware": traffic_aware,
        },
        "provider": "TraffiQ synthetic demo dataset",
        "is_demo_data": True,
        "live_traffic_available": False,
        "generated_at": data["generated_at"],
        "summary": {
            "routes_found": len(ranked),
            "recommended_route_id": ranked[0]["route_id"] if ranked else None,
            "fastest_estimated_duration_min": ranked[0]["estimated_duration_min"] if ranked else None,
        },
        "routes": ranked,
        "notice": "Synthetic sample data for demonstration only; not live traffic or navigation guidance.",
    }


@app.post("/api/v1/routes/recommend")
async def recommend_routes(request: RouteRequest):
    """Main endpoint for frontend integration. Demo mode works without internet."""
    use_sample = request.use_sample_data if request.use_sample_data is not None else DEMO_MODE

    if use_sample:
        data = load_sample_data()
        candidates = data["demo_routes"]
        ranked = rank_routes(candidates, traffic_aware=request.traffic_aware)
        return {
            "request": request.model_dump(),
            "provider": "TraffiQ synthetic demo dataset",
            "is_demo_data": True,
            "live_traffic_available": False,
            "routes": ranked,
            "recommended_route": ranked[0] if ranked else None,
            "notice": "Synthetic sample data only. Replace with Module 1 traffic observations for integrated traffic-aware recommendations.",
        }

    # OSRM requires coordinates, so this endpoint expects coordinates encoded in
    # the origin/destination strings as "longitude,latitude". Geocoding is out of scope.
    try:
        origin_lon, origin_lat = [float(x.strip()) for x in request.origin.split(",")]
        dest_lon, dest_lat = [float(x.strip()) for x in request.destination.split(",")]
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=422,
            detail='OSRM mode expects origin and destination as "longitude,latitude" strings. Example: "77.5946,12.9716".',
        )

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    )
    params = {
        "alternatives": "true",
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="OSRM request timed out.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach OSRM routing service.") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=404, detail="OSRM could not find a route for those coordinates.")

    routes = []
    for idx, item in enumerate(data["routes"]):
        duration = item["duration"] / 60
        routes.append({
            "route_id": f"osrm-{idx}",
            "name": f"OSRM Route {idx + 1}",
            "distance_km": round(item["distance"] / 1000, 2),
            "base_duration_min": round(duration, 1),
            "traffic_factor": 1.0,
            "congestion_level": "unknown",
            "congestion_score": None,
            "estimated_duration_min": round(duration, 1),
            "traffic_delay_min": 0.0,
            "traffic_aware": False,
            "rank": idx + 1,
            "recommended": idx == 0,
            "geometry": item.get("geometry"),
            "recommendation_reason": "Shortest OSRM duration; live traffic is not available from standard OSRM.",
        })

    routes.sort(key=lambda r: r["estimated_duration_min"])
    for idx, route in enumerate(routes, start=1):
        route["rank"] = idx
        route["recommended"] = idx == 1

    return {
        "request": request.model_dump(),
        "provider": "OSRM",
        "is_demo_data": False,
        "live_traffic_available": False,
        "routes": routes,
        "recommended_route": routes[0] if routes else None,
        "notice": "Standard OSRM duration is not live-traffic-aware. Integrate Module 1 observations or a traffic-aware provider.",
    }


@app.get("/api/v1/traffic/road-status")
def road_status():
    """Sample traffic status feed, designed to be replaced by Module 1."""
    data = load_sample_data()
    return {
        "provider": "synthetic demo dataset",
        "is_demo_data": True,
        "observations": data["traffic_observations"],
        "notice": "Replace this sample feed with Module 1's real traffic observations during integration.",
    }
