"""Application settings.

All configuration lives here and can be overridden with environment variables
(prefix ``PARKING_``) or a ``.env`` file in the project root. Nothing sensitive
is hard-coded in the source code. Example::

    PARKING_DATABASE_URL=sqlite:///./my_parking.db
    PARKING_EDGE_THRESHOLD=0.04
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="PARKING_", extra="ignore"
    )

    app_name: str = "Smart Parking Detection System"
    app_version: str = "1.0.0"

    # AI detector selection and local YOLO model weights.
    detector: str = Field("yolo", validation_alias="PARKING_DETECTOR")
    yolo_model: str = Field("yolov8n.pt", validation_alias="YOLO_MODEL")

    # Database (SQLite file in the project folder by default).
    database_url: str = f"sqlite:///{(BASE_DIR / 'parking.db').as_posix()}"

    # Folders.
    parking_images_dir: Path = BASE_DIR / "parking_images"
    processed_images_dir: Path = BASE_DIR / "processed_images"

    # Upload limits.
    max_image_size_mb: int = Field(10, ge=1)
    max_video_size_mb: int = Field(100, ge=1)

    # Video processing: analyse every Nth frame, never more than N frames per
    # request, and require a new status to appear in N consecutive analysed
    # frames before it is saved (1 = save immediately).
    default_frame_interval: int = Field(30, ge=1)
    max_processed_frames: int = Field(300, ge=1)
    default_confirm_frames: int = Field(1, ge=1)

    # Detection tuning (see README "Detection algorithm").
    edge_threshold: float = Field(0.015, gt=0, lt=1)
    roi_margin_ratio: float = Field(0.08, ge=0, lt=0.4)

    @field_validator("database_url")
    @classmethod
    def use_psycopg2_for_postgres(cls, url: str) -> str:
        """Accept the common ``postgres://`` / ``postgresql://`` forms."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url

    def ensure_dirs(self) -> None:
        """Create the image folders if they do not exist yet."""
        self.parking_images_dir.mkdir(parents=True, exist_ok=True)
        self.processed_images_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
