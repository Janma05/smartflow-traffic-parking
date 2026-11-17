# SmartFlow — Traffic and Smart Parking Management System

This repository contains the SmartFlow project components. **Module 8 (Historical Data
and Analytics backend)** is documented in [`backend/README.md`](backend/README.md).

## Start Module 8
1. Install Python 3.10 or newer.
2. Install dependencies: `pip install -r requirements.txt`.
3. Optionally copy `.env.example` to `.env` and configure `DATABASE_URL`.
4. Run `uvicorn backend.main:app --reload` from the project root.
5. Open `http://127.0.0.1:8000/docs`.

SQLite is used by default for a quick local run; PostgreSQL can be configured with
`DATABASE_URL`. Do not commit `.env` files or database credentials.
