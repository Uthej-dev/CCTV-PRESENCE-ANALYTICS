from datetime import datetime
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.utils import to_object_id
from app.schemas.detection import CameraLiveStatus, EventOut, Page, PresenceSummary, TrackingSessionOut
from app.services import tracking_service
from app.workers.manager import manager

router = APIRouter(tags=["presence & tracking"])


def optional_camera_oid(camera_id: str | None) -> ObjectId | None:
    if camera_id is None:
        return None
    oid = to_object_id(camera_id)
    if oid is None:
        raise NotFoundError("Camera not found")
    return oid


def _live_for_user(user: dict) -> list[CameraLiveStatus]:
    return [
        CameraLiveStatus(**w.status())
        for w in manager.running()
        if w.owner_id == user["_id"]
    ]


@router.get("/presence/current", response_model=PresenceSummary)
async def presence_current(user: dict = Depends(get_current_user)):
    """Live occupancy across all of the user's running cameras."""
    cams = _live_for_user(user)
    return PresenceSummary(
        running_cameras=len(cams),
        in_view=sum(c.in_view for c in cams),
        inside=sum(c.inside for c in cams),
        entries=sum(c.entries for c in cams),
        exits=sum(c.exits for c in cams),
        cameras=cams,
    )


@router.get("/detections", response_model=list[CameraLiveStatus])
async def detections(camera_id: str | None = None, user: dict = Depends(get_current_user)):
    """Latest-frame detections (tracked people with boxes) per running camera."""
    cams = _live_for_user(user)
    if camera_id:
        cams = [c for c in cams if c.camera_id == camera_id]
    return cams


@router.get("/tracking", response_model=Page[TrackingSessionOut])
async def tracking_sessions(
    camera_id: str | None = None,
    status: Literal["active", "closed"] | None = None,
    start: datetime | None = Query(None, description="first_seen >= start (ISO 8601)"),
    end: datetime | None = Query(None, description="first_seen < end (ISO 8601)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    """Presence sessions: one per tracked person visit, with duration."""
    docs, total = await tracking_service.list_sessions(
        user["_id"], optional_camera_oid(camera_id), status, start, end, skip, limit
    )
    items = [
        TrackingSessionOut(id=str(d["_id"]), camera_id=str(d["camera_id"]),
                           **{k: d.get(k) for k in TrackingSessionOut.model_fields if k not in ("id", "camera_id")})
        for d in docs
    ]
    return Page(items=items, total=total, skip=skip, limit=limit)


@router.get("/events", response_model=Page[EventOut])
async def entry_exit_events(
    camera_id: str | None = None,
    type: Literal["entry", "exit"] | None = None,
    start: datetime | None = Query(None, description="timestamp >= start (ISO 8601)"),
    end: datetime | None = Query(None, description="timestamp < end (ISO 8601)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    """Entry / exit history (line crossings)."""
    docs, total = await tracking_service.list_events(
        user["_id"], optional_camera_oid(camera_id), type, start, end, skip, limit
    )
    items = [
        EventOut(
            id=str(d["_id"]),
            camera_id=str(d["camera_id"]),
            session_id=str(d["session_id"]) if d.get("session_id") else None,
            person_id=d["person_id"],
            track_id=d["track_id"],
            type=d["type"],
            timestamp=d["timestamp"],
        )
        for d in docs
    ]
    return Page(items=items, total=total, skip=skip, limit=limit)
