# Module 7 demo
1. Start server and open `/docs`; show `/health`.
2. Show parking, road, camera and sensor records.
3. Run POST `/api/v1/monitoring/run`.
4. GET `/api/v1/alerts`: expect parking nearly-full, severe congestion, offline camera and stale sensor alerts.
5. Show summary, acknowledge and resolve an alert.
6. Update PARK-002 occupancy to 145/150 to trigger parking alert.
7. Explain email/FCM require credentials.

Say clearly: prototype uses synthetic inputs; live hardware/data integration, scheduled monitoring and database persistence are integration work.
