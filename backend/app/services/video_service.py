"""Video library: files in VIDEO_DIR that cameras with source_type=file can play."""
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ConflictError, ValidationError
from app.cv.video_source import VIDEO_EXTENSIONS, video_dir

CHUNK = 1024 * 1024


def _describe(path: Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    }


def list_videos() -> list[dict]:
    base = video_dir()
    if not base.is_dir():
        return []
    files = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
    return [_describe(p) for p in sorted(files, key=lambda p: p.name.lower())]


def _safe_name(filename: str) -> str:
    stem, suffix = Path(filename).stem, Path(filename).suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        raise ValidationError(f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(VIDEO_EXTENSIONS))}")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.") or "video"
    return f"{stem[:80]}{suffix}"


def _is_readable_video(path: Path) -> bool:
    cap = cv2.VideoCapture(str(path))
    try:
        ok, _ = cap.read()
        return ok
    finally:
        cap.release()


async def save_upload(upload: UploadFile) -> dict:
    name = _safe_name(upload.filename or "")
    base = video_dir()
    base.mkdir(parents=True, exist_ok=True)
    dest = base / name
    if dest.exists():
        raise ConflictError(f"A video named '{name}' already exists")

    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with tmp.open("wb") as f:
            while chunk := await upload.read(CHUNK):
                written += len(chunk)
                if written > limit:
                    raise ValidationError(f"File is larger than {settings.MAX_UPLOAD_MB} MB")
                f.write(chunk)
        if not await asyncio.to_thread(_is_readable_video, tmp):
            raise ValidationError("The file could not be decoded as a video")
        tmp.rename(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return _describe(dest)
