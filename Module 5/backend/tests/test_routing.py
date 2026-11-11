from app.main import rank_routes, load_sample_data

def test_sample_routes_are_ranked_fastest_first():
    data = load_sample_data()
    routes = rank_routes(data["demo_routes"], traffic_aware=True)
    assert len(routes) == 3
    assert routes[0]["recommended"] is True
    assert routes[0]["rank"] == 1
    assert routes[0]["estimated_duration_min"] <= routes[1]["estimated_duration_min"]

def test_no_traffic_uses_base_duration():
    data = load_sample_data()
    routes = rank_routes(data["demo_routes"], traffic_aware=False)
    assert all(r["estimated_duration_min"] == r["base_duration_min"] for r in routes)
    assert routes[0]["route_id"] == "R1"
