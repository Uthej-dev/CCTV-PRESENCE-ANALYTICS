"""Per-camera video recorder used by CameraWorker.

Every processed (annotated) frame is passed to on_frame(). While nobody is in
view, frames only go into a short pre-roll buffer. When someone appears a clip
starts, beginning with the buffered pre-roll, so the clip shows the person
walking in. The clip ends RECORDING_POST_ROLL_SECONDS after the last person leaves.
"""
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from bson import ObjectId

from app.core.config import settings
from app.cv.clip_writer import ClipWriter, output_size
from app.cv.recording_policy import RecordingPolicy
from app.services.recording_service import RecordingStore

logger = logging.getLogger(__name__)

MAX_MARKS = 2000


@dataclass
class ActiveClip:
    clip_id: ObjectId
    path: Path
    writer: ClipWriter
    start_time: datetime
    max_people: int = 0
    poster: np.ndarray | None = None
    person_ids: set = field(default_factory=set)
    marks: list = field(default_factory=list)
    events: list = field(default_factory=list)
    last_count: int = -1


class Recorder:
    def __init__(self, camera_id: ObjectId, owner_id: ObjectId, width: int, height: int):
        self.store = RecordingStore(camera_id, owner_id)
        self.policy = RecordingPolicy(settings.RECORDING_POST_ROLL_SECONDS, settings.RECORDING_MAX_CLIP_SECONDS)
        self.fps = settings.PROCESS_FPS
        self.size = output_size(width, height, settings.RECORDING_MAX_WIDTH)
        self.pre_roll: deque = deque(maxlen=max(1, int(settings.RECORDING_PRE_ROLL_SECONDS * self.fps)))
        self.clip: ActiveClip | None = None

    @property
    def recording(self) -> bool:
        return self.clip is not None

    def _fit(self, frame: np.ndarray) -> np.ndarray:
        if (frame.shape[1], frame.shape[0]) != self.size:
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        return frame

    def on_frame(self, now: datetime, mono: float, frame: np.ndarray, in_view: int,
                 person_ids: list[str], crossings: list) -> None:
        small = self._fit(frame)
        for action in self.policy.update(mono, in_view):
            if action == "stop":
                self._finish()
            else:
                self._start(now, mono)
        if self.clip:
            self._add(small, mono, in_view, person_ids, crossings)
        else:
            self.pre_roll.append((now, mono, small))

    def _start(self, now: datetime, mono: float) -> None:
        buffered = list(self.pre_roll)
        self.pre_roll.clear()
        start_time, start_mono = (buffered[0][0], buffered[0][1]) if buffered else (now, mono)
        clip_id, path = self.store.new_clip(start_time)
        writer = ClipWriter(path, self.size, self.fps, start_mono, crf=settings.RECORDING_CRF)
        self.clip = ActiveClip(clip_id, path, writer, start_time)
        for _, m, f in buffered:
            self._add(f, m, 0, [], [])

    def _add(self, frame, mono, in_view, person_ids, crossings) -> None:
        clip = self.clip
        try:
            clip.writer.write(frame, mono)
        except (BrokenPipeError, OSError):
            logger.exception("Recording %s: ffmpeg pipe failed", clip.clip_id)
            clip.writer.abort()
            self.store.discard(clip.clip_id, clip.path)
            self.clip = None
            return
        offset = round(mono - clip.writer.start_mono, 2)
        if in_view != clip.last_count and len(clip.marks) < MAX_MARKS:
            clip.marks.append({"offset": offset, "in_view": in_view})
            clip.last_count = in_view
        if in_view > clip.max_people:
            clip.max_people = in_view
            clip.poster = frame  # the busiest moment makes the thumbnail
        clip.person_ids.update(person_ids)
        for e in crossings:
            clip.events.append({"offset": offset, "type": e.type, "person_id": e.person_id})

    def _finish(self) -> None:
        clip, self.clip = self.clip, None
        if clip is None:
            return
        if not clip.writer.close():
            logger.warning("Recording %s failed to encode; discarded", clip.clip_id)
            self.store.discard(clip.clip_id, clip.path)
            return
        if clip.poster is not None:
            cv2.imwrite(str(clip.path.with_suffix(".jpg")), clip.poster, [cv2.IMWRITE_JPEG_QUALITY, 80])
        duration = clip.writer.duration
        self.store.complete(clip.clip_id, {
            "end_time": clip.start_time + timedelta(seconds=duration),
            "duration_seconds": round(duration, 2),
            "max_people": clip.max_people,
            "person_ids": sorted(clip.person_ids),
            "entries": sum(1 for e in clip.events if e["type"] == "entry"),
            "exits": sum(1 for e in clip.events if e["type"] == "exit"),
            "marks": clip.marks,
            "events": clip.events,
            "size_bytes": clip.path.stat().st_size,
        })
        logger.info("Recording saved: %s (%.1fs, max %d people)", clip.path.name, duration, clip.max_people)

    def close(self) -> None:
        """Camera stopping: finish the clip in progress."""
        self._finish()
