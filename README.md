# Smart Parking Detection — Integrated Project

This project combines the existing FastAPI parking backend, a separate YOLO AI detector, and the React dashboard.

## Final structure

```text
smart_parking_integrated/
├── backend/
│   ├── app/                 # FastAPI routes, services, database and models
│   ├── ai/                  # YOLO vehicle detection engine
│   ├── scripts/             # Sample-data generation and database seeding
│   ├── tests/               # Backend tests
│   ├── parking_images/      # Existing sample media
│   ├── processed_images/    # Annotated detection output
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/                 # React dashboard
    ├── package.json
    └── vite.config.js
```

## What each part does

- **Backend (`backend/app`)**: FastAPI endpoints, parking-space CRUD, database storage, summaries, image/video upload handling and annotated output.
- **AI (`backend/ai`)**: YOLOv8 vehicle detection for cars, motorcycles, buses and trucks. The AI detector implements the backend's detector interface, so the existing CRUD/database/services stay in place.
- **Frontend (`frontend`)**: React dashboard that calls the backend, uploads images/videos, and displays occupied/vacant totals and annotated images.

The backend database stores rectangular parking-space coordinates (`x`, `y`, `width`, `height`). These rectangles must be calibrated to the camera image. YOLO detects vehicles; the AI marks a bay occupied when a detected vehicle overlaps that bay.

## Windows setup (PowerShell)

Open **three terminal windows** in VS Code.

### 1. Backend + AI dependencies

```powershell
cd path	o\smart_parking_integratedackend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r ai\requirements.txt
```

The YOLO weights file `yolov8n.pt` is downloaded by Ultralytics the first time detection runs. An internet connection is needed for that first download unless you already have the model weights locally.

### 2. Configure the AI engine

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

The default is:

```env
PARKING_DETECTOR=yolo
```

Optional: if you want to test the backend without installing/downloading YOLO, change it to:

```env
PARKING_DETECTOR=edge
```

The edge detector is a basic OpenCV fallback. YOLO is the AI detection engine included for this integration.

### 3. Start the backend

From the `backend` folder, with the virtual environment activated:

```powershell
uvicorn app.main:app --reload --port 8000
```

Check:
- Backend health: http://127.0.0.1:8000/health
- API documentation: http://127.0.0.1:8000/docs

The database tables are created automatically. If the database has no parking spaces, open a second backend terminal, activate the same environment, and run:

```powershell
python -m scripts.seed_sample_spaces
```

This inserts the sample rectangular parking spaces only when the table is empty. Existing rows are not overwritten. To replace them with the sample spaces:

```powershell
python -m scripts.seed_sample_spaces --reset
```

### 4. Start the React frontend

Open a new terminal:

```powershell
cd path\to\smart_parking_integrated\frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually http://localhost:5173.

The frontend uses `http://127.0.0.1:8000` by default. To change it, copy `frontend/.env.example` to `frontend/.env` and set `VITE_API_URL`.

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend/database health |
| GET | `/api/parking/spaces` | List parking spaces and current status |
| GET | `/api/parking/summary` | Occupied/vacant totals and percentages |
| POST | `/api/parking/spaces` | Add a parking-space rectangle |
| PUT | `/api/parking/spaces/{space_id}` | Update a parking space |
| DELETE | `/api/parking/spaces/{space_id}` | Delete a parking space |
| POST | `/api/parking/detect/image` | Analyze an uploaded image using the selected detector |
| POST | `/api/parking/detect/video` | Analyze sampled frames from an uploaded video |
| POST | `/api/parking/detect/simulate` | Simulate occupancy without AI/camera |
| GET | `/api/parking/processed/{filename}` | Retrieve an annotated output image |

## Important calibration note

The sample parking-space rectangles are example coordinates. They will not automatically match a different CCTV/camera view. Add or update spaces through the API (Swagger UI at `/docs`) using pixel coordinates from your own camera image. If the rectangles are not calibrated, the occupancy result will be unreliable even when YOLO detects vehicles correctly.

This implementation analyzes uploaded images or recorded videos. It does not provide continuous live CCTV streaming. The sensor-update API from the separate starter is not required for the current dashboard.

## Tests

Run from the `backend` folder. The existing backend tests use the edge detector so they do not require YOLO weights:

PowerShell:
```powershell
$env:PARKING_DETECTOR = "edge"
python -m pytest -v
```

After testing, restart the server with `PARKING_DETECTOR=yolo` in `.env` to use the AI detector.

## Notes

- Keep `.env` private; do not upload database passwords or secrets.
- Do not copy a virtual environment from another computer. Create a fresh `.venv` using the steps above.
- YOLO's pretrained COCO model detects vehicle classes; parking-bay geometry still needs camera-specific calibration.
- Real-world accuracy must be evaluated against labelled footage from the target camera before relying on the results.
