from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


class LivePerson(BaseModel):
    person_id: str
    track_id: int
    first_seen: datetime
    duration_seconds: float
    box: list[float]  # [x1, y1, x2, y2] in pixels


class CameraLiveStatus(BaseModel):
    camera_id: str
    camera_name: str
    state: Literal["starting", "running", "error", "stopped"]
    error: str | None = None
    started_at: datetime
    fps: float = 0
    frame_width: int = 0
    frame_height: int = 0
    in_view: int = 0
    inside: int = 0
    entries: int = 0
    exits: int = 0
    last_frame_at: datetime | None = None
    recording: bool = False
    people: list[LivePerson] = []


class PresenceSummary(BaseModel):
    running_cameras: int
    in_view: int          # people currently detected across all running cameras
    inside: int           # net occupancy from line crossings
    entries: int          # since the cameras were started
    exits: int
    cameras: list[CameraLiveStatus]


class TrackingSessionOut(BaseModel):
    id: str
    camera_id: str
    person_id: str
    track_id: int
    status: Literal["active", "closed"]
    first_seen: datetime
    last_seen: datetime
    duration_seconds: float
    entry_time: datetime | None = None
    exit_time: datetime | None = None


class EventOut(BaseModel):
    id: str
    camera_id: str
    session_id: str | None = None
    person_id: str
    track_id: int
    type: Literal["entry", "exit"]
    timestamp: datetime
