# Tomorrow's demo script (3–5 minutes)

1. Start the API and open Swagger.
2. Show `/health` to prove the service is running.
3. Run `GET /api/v1/routes/sample` with traffic-aware mode enabled.
4. Explain: the sample set includes three candidate routes; the backend estimates adjusted travel time and ranks routes from fastest to slowest.
5. Run `POST /api/v1/routes/recommend` with `use_sample_data: true`.
6. Run it again with `traffic_aware: false`; explain the difference between base travel duration and a traffic-adjusted estimate.
7. Show `/api/v1/traffic/road-status`; explain this is the expected integration contract for Module 1, not a live feed yet.
8. Show the frontend handoff document and explain the React team can call the POST endpoint and render `routes`, `recommended`, and `geometry`.

Honest caveat to say aloud:
"Today this is a working backend prototype using synthetic demo data. It demonstrates route comparison and traffic-based ranking. The live version will consume Module 1's traffic observations. Standard OSRM provides route geometry and base duration but does not itself provide live traffic congestion."
