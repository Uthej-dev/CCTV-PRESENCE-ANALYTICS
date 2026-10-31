from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import get_current_user, get_current_user_from_query
from app.api.detections import optional_camera_oid
from app.schemas.detection import Page
from app.services import recording_service

router = APIRouter(prefix="/recordings", tags=["recordings"])


class Mark(BaseModel):
    offset: float  # seconds into the clip
    in_view: int


class ClipEvent(BaseModel):
    offset: float
    type: Literal["entry", "exit"]
    person_id: str


class RecordingOut(BaseModel):
    id: str
    camera_id: str
    status: Literal["recording", "complete"]
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    max_people: int
    person_ids: list[str]
    entries: int
    exits: int
    marks: list[Mark]
    events: list[ClipEvent]
    size_bytes: int


class RecordingAt(BaseModel):
    recording: RecordingOut
    offset_seconds: float


def _out(d: dict) -> RecordingOut:
    return RecordingOut(id=str(d["_id"]), camera_id=str(d["camera_id"]),
                        **{k: d[k] for k in RecordingOut.model_fields if k not in ("id", "camera_id")})


@router.get("", response_model=Page[RecordingOut])
async def list_recordings(
    camera_id: str | None = None,
    start: datetime | None = Query(None, description="clips overlapping [start, end) (ISO 8601)"),
    end: datetime | None = Query(None),
    min_people: int | None = Query(None, ge=1, description="clips where at least this many people were in view at once"),
    person_id: str | None = Query(None, description="clips showing this person, e.g. P-0012"),
    order: Literal["newest", "oldest"] = "newest",
    skip: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """Video clips recorded automatically while people were in view."""
    docs, total = await recording_service.list_recordings(
        user["_id"], optional_camera_oid(camera_id), start, end, min_people, person_id, skip, limit,
        oldest_first=order == "oldest",
    )
    return Page(items=[_out(d) for d in docs], total=total, skip=skip, limit=limit)


@router.get("/at", response_model=RecordingAt)
async def recording_at(
    at: datetime = Query(..., description="ISO 8601 moment to look up"),
    camera_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """The clip covering a moment and the offset to seek to ("show me 10:32")."""
    doc, offset = await recording_service.recording_at(user["_id"], at, optional_camera_oid(camera_id))
    return RecordingAt(recording=_out(doc), offset_seconds=round(offset, 2))


@router.get("/{recording_id}/video", responses={200: {"content": {"video/mp4": {}}}})
async def video(recording_id: str, user: dict = Depends(get_current_user_from_query)):
    """The MP4 (supports HTTP Range requests, so the browser can seek). Accepts ?token=."""
    doc = await recording_service.get_recording(user["_id"], recording_id)
    return FileResponse(recording_service.file_path(doc, "path"), media_type="video/mp4",
                        headers={"Cache-Control": "private, max-age=86400"})


@router.get("/{recording_id}/poster", responses={200: {"content": {"image/jpeg": {}}}})
async def poster(recording_id: str, user: dict = Depends(get_current_user_from_query)):
    """Thumbnail: the busiest moment of the clip. Accepts ?token=."""
    doc = await recording_service.get_recording(user["_id"], recording_id)
    return FileResponse(recording_service.file_path(doc, "poster_path"), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(recording_id: str, user: dict = Depends(get_current_user)):
    await recording_service.delete_recording(user["_id"], recording_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
