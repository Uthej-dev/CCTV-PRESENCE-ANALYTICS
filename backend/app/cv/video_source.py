"""Uniform frame reader for video files, webcams and RTSP streams.

- file:   played back at its native FPS and looped, so it behaves like a live camera
- webcam: device index (on macOS the terminal needs camera permission)
- rtsp:   opened with FFmpeg and re-opened automatically if the stream drops
"""
import time
from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings


class VideoSourceError(Exception):
    pass


VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def video_dir() -> Path:
    return Path(settings.VIDEO_DIR).resolve()


def resolve_file_path(source: str) -> Path:
    """Map a file source to a path inside VIDEO_DIR. Paths escaping it (absolute, ../) are rejected,
    so a camera can never be pointed at arbitrary files on the server."""
    base = video_dir()
    path = (base / source).resolve()
    if not path.is_relative_to(base):
        raise VideoSourceError(f"File sources must be inside the video directory: {source}")
    return path


def file_exists(source: str) -> bool:
    try:
        return resolve_file_path(source).is_file()
    except VideoSourceError:
        return False


class VideoSource:
    def __init__(self, source_type: str, source: str):
        self.source_type = source_type
        self.source = source
        self.cap: cv2.VideoCapture | None = None
        self.fps = 25.0
        self.width = 0
        self.height = 0
        self.looped = False  # set to True on the read that restarts a file

    @property
    def is_file(self) -> bool:
        return self.source_type == "file"

    def open(self) -> None:
        if self.source_type == "file":
            path = resolve_file_path(self.source)
            if not path.is_file():
                raise VideoSourceError(f"Video file not found: {path}")
            cap = cv2.VideoCapture(str(path))
        elif self.source_type == "webcam":
            cap = cv2.VideoCapture(int(self.source))
        elif self.source_type == "rtsp":
            cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # keep latency low
        else:
            raise VideoSourceError(f"Unsupported source type: {self.source_type}")

        if not cap.isOpened():
            raise VideoSourceError(f"Could not open {self.source_type} source: {self.source}")

        self.cap = cap
        fps = cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if fps and 1 <= fps <= 120 else 25.0
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def skip(self, n: int) -> None:
        """Drop n frames without decoding them (used to keep file playback real-time)."""
        for _ in range(n):
            if not self.cap.grab():
                break

    def read(self) -> np.ndarray:
        self.looped = False
        ok, frame = self.cap.read()
        if ok:
            return frame

        if self.is_file:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
            if ok:
                self.looped = True
                return frame
            raise VideoSourceError("Could not read from video file")

        if self.source_type == "rtsp":
            # Try to reconnect a few times with backoff before giving up
            for attempt in range(5):
                time.sleep(min(2 ** attempt, 10))
                self.release()
                try:
                    self.open()
                    ok, frame = self.cap.read()
                    if ok:
                        return frame
                except VideoSourceError:
                    continue
        raise VideoSourceError(f"Lost {self.source_type} source: {self.source}")

    def release(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
