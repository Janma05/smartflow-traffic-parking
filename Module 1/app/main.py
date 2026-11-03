from pathlib import Path
import shutil
import tempfile
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.traffic_service import analyze_video


app = FastAPI(
    title="TraffiQ Module 1 - Real-Time Traffic Monitoring",
    version="1.0.0",
)

# Folder for saving annotated videos.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Supported video formats.
SUPPORTED_FORMATS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".mpeg",
    ".mpg",
}


@app.get("/")
def root():
    """Check whether the TraffiQ application is running."""
    return {
        "project": "TraffiQ",
        "module": "Real-Time Traffic Monitoring",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/traffic/health")
def health():
    """Check the health of the traffic-monitoring API."""
    return {
        "status": "ok",
        "module": "traffic-monitoring",
    }


@app.post("/api/traffic/analyze")
async def analyze_traffic(file: UploadFile = File(...)):
    """Analyze an uploaded traffic video."""

    filename = file.filename or "uploaded_video"
    suffix = Path(filename).suffix.lower()

    # Validate the uploaded file extension.
    if suffix not in SUPPORTED_FORMATS:
        await file.close()

        raise HTTPException(
            status_code=400,
            detail=(
                "Upload a supported video file: "
                "MP4, AVI, MOV, MKV, MPEG, or MPG."
            ),
        )

    temp_path = None
    output_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.mp4"

    try:
        # Save the uploaded video temporarily.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp:
            temp_path = Path(temp.name)
            shutil.copyfileobj(file.file, temp)

        # Analyze the uploaded video and create its annotated version.
        result = analyze_video(
            str(temp_path),
            output_path=str(output_path),
        )

        # Verify that the annotated video was generated.
        if (
            not output_path.is_file()
            or output_path.stat().st_size == 0
        ):
            raise RuntimeError(
                "Video analysis completed, but the annotated "
                "video could not be generated."
            )

        return {
            "filename": filename,
            **result,
            "annotated_video_url": (
                f"/api/traffic/videos/{output_path.name}"
            ),
        }

    except RuntimeError as exc:
        # Expected video-processing errors.
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Keep internal error details in the server logs.
        print(f"Traffic analysis failed: {exc}")

        raise HTTPException(
            status_code=500,
            detail=(
                "Traffic analysis failed. "
                "Check the server logs."
            ),
        ) from exc

    finally:
        await file.close()

        # Delete the temporary uploaded file.
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


@app.get("/api/traffic/videos/{filename}")
def get_annotated_video(filename: str):
    """Serve a generated annotated MP4 video."""

    # Only allow UUID-based MP4 filenames.
    if (
        Path(filename).name != filename
        or not filename.endswith(".mp4")
        or len(filename) != 36
        or not all(
            character in "0123456789abcdef"
            for character in filename[:-4]
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid video filename.",
        )

    video_path = OUTPUT_DIR / filename

    if not video_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Annotated video not found.",
        )

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename,
    )
