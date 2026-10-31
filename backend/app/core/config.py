from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "CCTV Human Detection & Presence Analytics"
    ENVIRONMENT: str = "development"

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "cctv_analytics"

    # Auth (used from Stage 4)
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Comma-separated list of allowed frontend origins
    CORS_ORIGINS: str = "http://localhost:5173"

    # Computer vision
    VIDEO_DIR: str = "videos"                 # file sources are resolved relative to this
    YOLO_MODEL: str = "weights/yolo11n.pt"    # downloaded automatically on first use
    YOLO_DEVICE: str = ""                     # "" = auto (cuda > mps > cpu), or "cpu", "mps", "cuda:0"
    DETECTION_CONFIDENCE: float = 0.35
    PROCESS_FPS: float = 12.0                 # max frames/sec run through YOLO per camera
    TRACK_LOST_SECONDS: float = 2.0           # a track unseen this long ends its session
    MIN_TRACK_HITS: int = 4                   # frames a track must be seen before it counts as a person
    LINE_DEAD_ZONE: float = 0.01              # hysteresis around the line, fraction of frame diagonal
    SNAPSHOT_INTERVAL_SECONDS: float = 10.0   # how often occupancy samples are stored
    MAX_RUNNING_CAMERAS: int = 4
    STREAM_JPEG_QUALITY: int = 70

    # Analytics
    TIMEZONE: str = "UTC"                     # default timezone for "today" when the client sends none
    MIN_VISIT_SECONDS: float = 1.0            # shorter sessions are tracker noise, not visitors
    SNAPSHOT_RETENTION_DAYS: int = 90         # occupancy samples older than this are deleted (TTL index)

    # Uploads
    MAX_UPLOAD_MB: int = 200

    # Video recordings: annotated MP4 clips recorded while people are in view
    MEDIA_DIR: str = "media"
    RECORDING_ENABLED: bool = True
    RECORDING_PRE_ROLL_SECONDS: float = 2.0   # footage kept from just BEFORE someone appears
    RECORDING_POST_ROLL_SECONDS: float = 5.0  # keep recording this long after the last person leaves
    RECORDING_MAX_CLIP_SECONDS: float = 300.0 # long activity is split into clips of this length
    RECORDING_RETENTION_DAYS: int = 7         # older clips (files + DB docs) are deleted
    RECORDING_MAX_WIDTH: int = 960            # clips are downscaled to at most this width
    RECORDING_CRF: int = 28                   # H.264 quality: lower = better quality, bigger files

    @model_validator(mode="after")
    def _check_production_secret(self):
        if self.ENVIRONMENT == "production" and (len(self.JWT_SECRET) < 32 or "change" in self.JWT_SECRET
                                                 or "replace" in self.JWT_SECRET):
            raise ValueError("JWT_SECRET must be a random string of at least 32 characters in production")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
