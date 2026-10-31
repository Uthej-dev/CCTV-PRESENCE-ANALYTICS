from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.services import video_service
from app.workers.manager import manager

router = APIRouter(tags=["system"])


class VideoOut(BaseModel):
    name: str
    size_bytes: int
    modified_at: datetime


class SystemInfo(BaseModel):
    app: str
    version: str
    environment: str
    yolo_model: str
    yolo_device: str
    process_fps: float
    max_running_cameras: int
    running_cameras: int
    min_visit_seconds: float
    default_timezone: str
    max_upload_mb: int


@router.get("/videos", response_model=list[VideoOut])
async def list_videos(_: dict = Depends(get_current_user)):
    """Video files available as camera sources (source_type=file)."""
    return video_service.list_videos()


@router.post("/videos", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...), _: dict = Depends(get_current_user)):
    """Upload a video file to the library (mp4/avi/mov/mkv/webm)."""
    return await video_service.save_upload(file)


@router.get("/system/info", response_model=SystemInfo)
async def system_info(_: dict = Depends(get_current_user)):
    from app.cv.detector import pick_device  # imported lazily: pulls in torch

    return SystemInfo(
        app=settings.APP_NAME,
        version="1.0.0",
        environment=settings.ENVIRONMENT,
        yolo_model=settings.YOLO_MODEL,
        yolo_device=pick_device(),
        process_fps=settings.PROCESS_FPS,
        max_running_cameras=settings.MAX_RUNNING_CAMERAS,
        running_cameras=len(manager.running()),
        min_visit_seconds=settings.MIN_VISIT_SECONDS,
        default_timezone=settings.TIMEZONE,
        max_upload_mb=settings.MAX_UPLOAD_MB,
    )
