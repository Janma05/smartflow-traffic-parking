# Smart Parking Detection System (Module 2 – Python Backend)

A FastAPI backend that detects **occupied** and **vacant** parking spaces in images and videos with OpenCV, stores the latest status of every space in SQLite, and calculates parking availability.

> **Honest status:** the backend, API and tests are complete and pass (46 tests; also verified against PostgreSQL 16). The detection algorithm was only tested on the **synthetic drawings** in `parking_images/`. It has **not** been tested on real parking-lot footage, so no real-world accuracy is claimed. See [Detection algorithm and limitations](#detection-algorithm-and-limitations).

---

## 1. What each file does

```
smart_parking_detection/
├── app/
│   ├── __init__.py          Marks "app" as a Python package.
│   ├── main.py              Creates the FastAPI app, runs start-up (creates folders + SQLite tables),
│   │                        and defines GET / and GET /health.
│   ├── config.py            All settings (database URL, thresholds, upload limits). Reads environment
│   │                        variables / .env, so nothing sensitive lives in the code.
│   ├── database.py          SQLAlchemy engine, session factory, get_db() dependency, init_db().
│   ├── models.py            The ParkingSpace database table.
│   ├── schemas.py           Pydantic models that validate requests and shape responses.
│   ├── crud.py              Database operations: create/read/update/delete, counting, and
│   │                        apply_statuses() which writes only the spaces that really changed.
│   ├── detector.py          OpenCV detection (BaseDetector interface + EdgeDensityDetector) and the
│   │                        red/green image annotation. This is the file to replace with YOLO later.
│   ├── services.py          Business logic: summary formulas, upload validation, image/video/
│   │                        simulation processing.
│   └── routers/
│       ├── __init__.py
│       └── parking.py       The /api/parking/... endpoints (thin: validate, call services, return).
├── parking_images/          Sample images, sample video and sample_spaces.json (synthetic).
├── processed_images/        Annotated output images are saved here.
├── scripts/
│   ├── generate_samples.py  Re-creates the sample images/video (and is used by the tests).
│   └── seed_sample_spaces.py Loads the 10 sample spaces into the database.
├── tests/
│   └── test_parking.py      46 automated tests (pytest + TestClient).
├── pytest.ini               Tells pytest where the project root is.
├── requirements.txt         Dependencies.
├── .env.example             Optional settings you can copy to ".env".
├── .gitignore
└── README.md                This file.
```

`config.py`, `scripts/`, `pytest.ini` and `.env.example` are small additions to the requested structure (settings, sample data, test setup).

---

## 2. Setup on Windows with VS Code

**Requirements:** Python 3.11 or newer ([python.org](https://www.python.org/downloads/) – tick **"Add python.exe to PATH"** in the installer) and VS Code with the **Python** extension.

1. Unzip the project and open the `smart_parking_detection` folder in VS Code (**File → Open Folder**).
2. Open a terminal: **Terminal → New Terminal** (it should be PowerShell).
3. Create a virtual environment:
   ```powershell
   python -m venv venv
   ```
4. Activate it (the prompt should start with `(venv)`):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
5. Install the dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
6. *(Optional but recommended)* load the 10 sample parking spaces that match the sample images:
   ```powershell
   python -m scripts.seed_sample_spaces
   ```
7. Run the application:
   ```powershell
   uvicorn app.main:app --reload
   ```
   The SQLite file `parking.db` and its tables are created automatically on first start.
8. Open Swagger UI in your browser: **http://127.0.0.1:8000/docs**
9. Run the automated tests (stop the server first, or open a second terminal with the venv activated):
   ```powershell
   pytest -v
   ```

**Select the interpreter in VS Code:** press `Ctrl+Shift+P` → **Python: Select Interpreter** → choose the one inside `.\venv`.

### Try it in Swagger UI (no camera needed)

1. `POST /api/parking/detect/simulate` → **Try it out** → Execute. Random occupancy is set.
2. `GET /api/parking/summary` shows the new counts.
3. `POST /api/parking/detect/image` → choose `parking_images/partial_lot.png` → Execute. 5 spaces become occupied. Open the `processed_image_url` in the response (add `http://127.0.0.1:8000` in front) to see the red/green image.
4. `POST /api/parking/detect/video` → choose `parking_images/sample_parking_video.mp4`, set `frame_interval` to `5`.

(Step 3 and 4 need the sample spaces from setup step 6, or your own spaces from `POST /api/parking/spaces`.)

---

## 2b. Using PostgreSQL instead of SQLite (step by step)

By default the app uses a local SQLite file, so nothing extra is needed. To use PostgreSQL instead, only the database URL changes; no code changes are needed. This was tested against PostgreSQL 16 (tables created automatically, image and video detection, validation constraints).

**Step 1 – Install PostgreSQL (Windows).** Download the installer from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/). Keep the default port `5432`, set a password for the `postgres` user and remember it. pgAdmin is included.

**Step 2 – Create a database and user.** Open **SQL Shell (psql)** from the Start menu (press Enter to accept the defaults, then type the `postgres` password) and run:
```sql
CREATE USER parking_user WITH PASSWORD 'choose_a_strong_password';
CREATE DATABASE parking_db OWNER parking_user;
```
(Or do the same in pgAdmin: *Login/Group Roles → Create*, then *Databases → Create*.)

**Step 3 – Install the driver.** It is already in `requirements.txt` (`psycopg2-binary`). If you installed the requirements earlier without it, run in the activated venv:
```powershell
pip install psycopg2-binary
```

**Step 4 – Tell the app to use PostgreSQL.** In the project root copy `.env.example` to `.env` (VS Code: right-click → Copy, Paste, Rename) and set this line:
```
PARKING_DATABASE_URL=postgresql://parking_user:choose_a_strong_password@localhost:5432/parking_db
```
Format: `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`. If the password contains special characters such as `@`, `#`, `/` or `%`, URL-encode them (`@` → `%40`, `#` → `%23`, `/` → `%2F`, `%` → `%25`). The `.env` file is git-ignored, so the password stays out of your source code.

**Step 5 – Start the app.** The `parking_spaces` table is created automatically on start:
```powershell
uvicorn app.main:app --reload
```

**Step 6 – Check the connection.** Open http://127.0.0.1:8000/health. You should see `{"status":"ok","database":"connected"}`. If you get `503`, see the troubleshooting table.

**Step 7 – Add data and look at it.**
```powershell
python -m scripts.seed_sample_spaces
```
Then use Swagger UI (http://127.0.0.1:8000/docs) as in section 2. To see the rows in PostgreSQL, run in pgAdmin's Query Tool (or psql):
```sql
SELECT id, name, status, last_updated FROM parking_spaces ORDER BY id;
```

**Switching back to SQLite:** delete or comment out the `PARKING_DATABASE_URL` line in `.env` and restart.

**Notes**
* The two databases are separate: spaces created in SQLite do not appear in PostgreSQL.
* Tests always use their own in-memory SQLite database, so `pytest -v` never touches your PostgreSQL data, even when `.env` points to it.
* There is no migration tool in this module. If you later change the model, drop the table (`DROP TABLE parking_spaces;`) and restart to recreate it, or add Alembic.

---

## 3. Configuration

Settings come from environment variables or a `.env` file (copy `.env.example` to `.env`). All are optional.

| Variable | Default | Meaning |
|---|---|---|
| `PARKING_DATABASE_URL` | `sqlite:///<project>/parking.db` | Database location (SQLite file or PostgreSQL URL, see section 2b) |
| `PARKING_EDGE_THRESHOLD` | `0.015` | Edge density at/above which a space counts as occupied |
| `PARKING_ROI_MARGIN_RATIO` | `0.08` | Border of each space ignored (skips painted lines) |
| `PARKING_DEFAULT_FRAME_INTERVAL` | `30` | Video: analyse every Nth frame |
| `PARKING_MAX_PROCESSED_FRAMES` | `300` | Video: max analysed frames per request |
| `PARKING_DEFAULT_CONFIRM_FRAMES` | `1` | Video: frames in a row needed before a change is saved |
| `PARKING_MAX_IMAGE_SIZE_MB` / `PARKING_MAX_VIDEO_SIZE_MB` | `10` / `100` | Upload limits |

---

## 4. API endpoints

| # | Method and path | Purpose | Success code |
|---|---|---|---|
| 1 | `GET /` | Welcome message | 200 |
| 2 | `GET /api/parking/spaces` | All spaces and statuses | 200 |
| 3 | `GET /api/parking/summary` | Totals and percentages | 200 |
| 4 | `GET /api/parking/spaces/{space_id}` | One space | 200 |
| 5 | `POST /api/parking/spaces` | Register a space | 201 |
| 6 | `PUT /api/parking/spaces/{space_id}` | Update details (or manually set status) | 200 |
| 7 | `DELETE /api/parking/spaces/{space_id}` | Delete a space | 204 |
| 8 | `POST /api/parking/detect/image` | Detect from an uploaded image | 200 |
| 9 | `POST /api/parking/detect/video` | Process an uploaded video | 200 |
| 10 | `POST /api/parking/detect/simulate` | Simulate occupancy (no camera) | 200 |
| 11 | `GET /health` | Backend + database check | 200 |
| – | `GET /api/parking/processed/{filename}` | Download an annotated image | 200 |

**Error codes:** `400` unreadable image/video, empty upload, or no spaces configured · `404` space not found · `413` file too large · `415` wrong file type · `422` invalid input (negative coordinates, zero width/height, bad id such as `abc` or `0`, bad `occupancy_rate`, empty `PUT` body, …).

### Example requests and real responses

These were produced by running the server with the sample data. Timestamps will differ on your machine. In **PowerShell** use `curl.exe` (plain `curl` is an alias for another command), or just use Swagger UI.

**Register a space**
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/parking/spaces -H "Content-Type: application/json" -d '{\"name\":\"Parking Space 1\",\"x\":40,\"y\":30,\"width\":130,\"height\":170}'
```
```json
{"id": 1, "name": "Parking Space 1", "x": 40, "y": 30, "width": 130, "height": 170,
 "status": "vacant", "last_updated": "2026-10-27T05:24:18.853085"}
```

**Update a space** (send only the fields that change; `status` is a manual override)
```powershell
curl.exe -X PUT http://127.0.0.1:8000/api/parking/spaces/1 -H "Content-Type: application/json" -d '{\"name\":\"VIP\"}'
```

**Detect from an image**
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/parking/detect/image -F "file=@parking_images/partial_lot.png;type=image/png"
```
```json
{
  "detector": "edge_density",
  "spaces_processed": 10,
  "status_changes": 5,
  "results": [
    {"space_id": 1, "name": "Parking Space 1", "status": "occupied", "occupancy_score": 0.0759, "changed": true},
    {"space_id": 2, "name": "Parking Space 2", "status": "vacant",   "occupancy_score": 0.0,    "changed": false}
    // ... one entry per space
  ],
  "summary": {"total_spaces": 10, "occupied_spaces": 5, "available_spaces": 5,
              "occupancy_percentage": 50.0, "availability_percentage": 50.0},
  "processed_image_url": "/api/parking/processed/processed_20261027_052419_388e3f61.png",
  "warnings": []
}
```
Add `?return_image=true` to receive the annotated PNG directly (counts are in the `X-Occupied-Spaces`, `X-Available-Spaces`, `X-Total-Spaces`, `X-Status-Changes` headers). Sending the same image again returns `"status_changes": 0` and writes nothing to the database.

**Process a video**
```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/parking/detect/video?frame_interval=5" -F "file=@parking_images/sample_parking_video.mp4;type=video/mp4"
```
Result for the sample video (60 frames, cars arrive and leave): `frames_read 60`, `frames_processed 12`, final `summary` of 6 occupied / 4 available (60.0 % / 40.0 %). Query parameters: `frame_interval` (analyse every Nth frame), `max_frames`, `confirm_frames` (a status change must appear in this many analysed frames in a row; use 2–3 to suppress flicker).

**Simulate occupancy**
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/parking/detect/simulate -H "Content-Type: application/json" -d '{\"occupancy_rate\":0.3,\"seed\":5}'
```
Marks exactly `round(0.3 × total)` random spaces occupied (same `seed` = same result). Body is optional (default rate 0.5).

**Summary** (always calculated from the database, never hard-coded)
```json
{"total_spaces": 10, "occupied_spaces": 3, "available_spaces": 7,
 "occupancy_percentage": 30.0, "availability_percentage": 70.0}
```
With zero spaces every number and both percentages are `0` / `0.0` (no division error).

**Space list** (`GET /api/parking/spaces`): each item contains `id`, `name`, `status`, `last_updated` as in your spec, plus `x`, `y`, `width`, `height`.

---

## 5. How automatic updates work

* Every detection request (image, video frame, simulation) compares the new status with the saved one.
* Only spaces whose status **changed** are written, and only they get a new `last_updated`. If nothing changed there is no database write at all.
* The summary is calculated from the database on every request, so it is always consistent with the saved statuses; detection responses include the fresh summary.
* Videos: `frame_interval` sets how often a frame is analysed; `confirm_frames` debounces flicker.

---

## 6. Detection algorithm and limitations

**Algorithm (`EdgeDensityDetector` in `app/detector.py`)**

1. Convert the frame to grayscale and apply a light Gaussian blur.
2. Run Canny edge detection once on the whole frame.
3. For each space rectangle, shrink it by 8 % on every side (ignores painted lines) and compute `edge density = edge pixels / pixels` inside it.
4. `density ≥ threshold` → **occupied**, otherwise **vacant**. Spaces outside the image are skipped and reported in `warnings`.
5. Save changed statuses, draw the result (**red = occupied, green = vacant**, grey = skipped).

**Tested:** only on the synthetic drawings (`parking_images/`). On them, empty spaces scored 0.0 and cars scored 0.025–0.093, so the default threshold `0.015` separates them. Real footage is noisier, so this separation should not be expected to carry over.

**Limitations – this basic method can be wrong with:**

* **Lighting:** night, glare, low sun and headlights add or hide edges.
* **Shadows and ground texture:** cracks, puddles, leaves, oil stains, gravel and markings can look busy and be marked occupied.
* **Plain vehicles:** a smooth or very dark car can have few edges and be marked vacant. Other objects (a pile of boxes, a trailer) look like cars.
* **Camera angle and movement:** rectangles are fixed pixel coordinates; if the camera moves or sees spaces at a steep angle, cars overlap neighbouring rectangles and you must reconfigure.
* **Weather:** rain, snow and fog change the edge pattern.
* **Calibration:** the threshold is camera-specific. Test with your own images and adjust `PARKING_EDGE_THRESHOLD`; measure accuracy on labelled footage before relying on it.

**Replacing it with YOLO later:** all other code depends only on the `BaseDetector` interface (`detect(image, regions) -> list[DetectionResult]`). To switch:

1. `pip install ultralytics`
2. In `app/detector.py`, add `class YoloDetector(BaseDetector)`: load the model once in `__init__`, run it in `detect()`, and mark a region `occupied` when a detected vehicle box overlaps it by more than about 30–50 % (compute the overlap yourself, tune it), otherwise `vacant`.
3. Return `YoloDetector(...)` from `get_detector()`.

No endpoint, schema or database change is needed.

---

## 7. Testing

```powershell
pytest -v
```

46 tests, each using a fresh in-memory database and a temporary folder (your real `parking.db` is never touched). They cover: creating, listing, reading, updating and deleting spaces; validation (negative coordinates, zero sizes, blank names); invalid and missing ids; summary maths including zero spaces; image detection on empty, partial and full lots; no database writes on repeated images; timestamps; red/green output image; invalid/corrupt/oversized uploads; video processing, frame interval and flicker debouncing; simulation; empty configuration; detector and debouncer unit tests.

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python with **Add to PATH** ticked, or try `py -m venv venv`. Restart VS Code. |
| PowerShell: *"running scripts is disabled on this system"* when activating | Run once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, then activate again. Or use Command Prompt: `venv\Scripts\activate.bat`. |
| `uvicorn` is not recognized | The venv is not active (no `(venv)` in the prompt). Activate it, or run `python -m uvicorn app.main:app --reload`. |
| `ModuleNotFoundError: No module named 'app'` (or `scripts`) | Run commands from the project root (the folder containing `app/`). Use `python -m scripts.seed_sample_spaces`, not `python scripts/...`. |
| `ModuleNotFoundError: fastapi` / `cv2` | Packages are not installed in the active interpreter: activate the venv, run `pip install -r requirements.txt`, and select the venv interpreter in VS Code. |
| `pip install` fails for OpenCV/NumPy | Upgrade pip (`python -m pip install --upgrade pip`) and use 64-bit Python 3.11+. |
| `Form data requires "python-multipart"` | `pip install python-multipart` (already in requirements). |
| `Address already in use` / port 8000 busy | `uvicorn app.main:app --reload --port 8001` and open `http://127.0.0.1:8001/docs`. |
| Swagger shows 400 "No parking spaces are configured" | Add spaces first (`POST /api/parking/spaces`) or run `python -m scripts.seed_sample_spaces`. |
| 415 on upload | Use jpg/png/bmp/webp images or mp4/avi/mov/mkv/webm videos. |
| 400 "not a valid, readable video" | The file is damaged or uses a codec your OpenCV build cannot decode. Re-encode to H.264 mp4. |
| Everything is detected as occupied/vacant on my images | Normal for an uncalibrated basic algorithm: check your rectangles on the annotated image, then adjust `PARKING_EDGE_THRESHOLD`. |
| `sqlite3.OperationalError: no such table` | Start the app via `uvicorn` (it creates tables on start) or run the seed script once. |
| Want a clean database | SQLite: stop the server and delete `parking.db`. PostgreSQL: run `DROP TABLE parking_spaces;` in pgAdmin. The table is recreated on the next start. |
| `/health` returns 503 or start-up shows `connection refused` | PostgreSQL is not running (Windows: *Services* → `postgresql-x64-NN` → Start), or the host/port in the URL is wrong. |
| `password authentication failed for user` | Wrong user or password in `PARKING_DATABASE_URL`. Special characters in the password must be URL-encoded (`@` → `%40`). |
| `database "parking_db" does not exist` | Create it first: `CREATE DATABASE parking_db OWNER parking_user;` |
| `permission denied for schema public` (PostgreSQL 15+) | As `postgres` run: `GRANT ALL ON SCHEMA public TO parking_user;` while connected to `parking_db`. |
| `No module named 'psycopg2'` | `pip install psycopg2-binary` in the activated venv. |
| `.env` changes are ignored | The file must be named exactly `.env` (not `.env.txt`) and be in the project root; restart `uvicorn`. |
| Tests fail only in VS Code Test Explorer | Run `pytest -v` in the terminal from the project root; make sure the interpreter is the venv. |
| Old annotated images pile up | Delete the files in `processed_images/` whenever you like. |

---

## 9. Notes

* No API keys or secrets are used. Configuration is via environment variables / `.env` (ignored by git).
* No authentication is implemented; add it before exposing the API outside your own machine.
* Runs locally without Docker. Frontend work should only start after this backend is verified against your own images.
