from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class SourceType(str, Enum):
    FILE = "file"      # path to a video file (relative to VIDEO_DIR or absolute)
    WEBCAM = "webcam"  # device index, e.g. "0"
    RTSP = "rtsp"      # rtsp://user:pass@host:554/stream


class CameraStatus(str, Enum):
    IDLE = "idle"        # never started / stopped
    RUNNING = "running"  # worker is processing frames
    ERROR = "error"      # worker failed (see last_error)


class EntryDirection(str, Enum):
    """Movement direction across the line that counts as an ENTRY."""
    DOWN = "down"
    UP = "up"
    LEFT = "left"
    RIGHT = "right"


class LineConfig(BaseModel):
    """Virtual entry/exit line in normalised coordinates (0..1 of frame width/height)."""
    x1: float = Field(0.0, ge=0, le=1)
    y1: float = Field(0.5, ge=0, le=1)
    x2: float = Field(1.0, ge=0, le=1)
    y2: float = Field(0.5, ge=0, le=1)

    @model_validator(mode="after")
    def _not_a_point(self):
        if (self.x1, self.y1) == (self.x2, self.y2):
            raise ValueError("line start and end points must differ")
        return self


def validate_source(source_type: SourceType, source: str) -> None:
    if source_type == SourceType.FILE and (source.startswith(("/", "\\")) or ".." in source.replace("\\", "/").split("/")):
        raise ValueError("file source must be a file name inside the video library (no absolute paths or '..')")
    if source_type == SourceType.WEBCAM and not source.isdigit():
        raise ValueError("webcam source must be a device index such as '0'")
    if source_type == SourceType.RTSP and not source.lower().startswith(("rtsp://", "rtsps://")):
        raise ValueError("rtsp source must start with rtsp:// or rtsps://")


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field("", max_length=200)
    source_type: SourceType = SourceType.FILE
    source: str = Field(min_length=1, max_length=500)
    is_active: bool = True
    line: LineConfig = Field(default_factory=LineConfig)
    entry_direction: EntryDirection = EntryDirection.DOWN


class CameraCreate(CameraBase):
    @model_validator(mode="after")
    def _check_source(self):
        validate_source(self.source_type, self.source)
        return self


class CameraUpdate(BaseModel):
    """All fields optional: only the fields sent are updated."""
    name: str | None = Field(None, min_length=1, max_length=100)
    location: str | None = Field(None, max_length=200)
    source_type: SourceType | None = None
    source: str | None = Field(None, min_length=1, max_length=500)
    is_active: bool | None = None
    line: LineConfig | None = None
    entry_direction: EntryDirection | None = None


class CameraOut(CameraBase):
    id: str
    status: CameraStatus
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

