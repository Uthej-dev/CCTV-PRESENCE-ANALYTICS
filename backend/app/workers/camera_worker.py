"""One background thread per running camera.

    VideoSource ─▶ PersonTracker (YOLO + ByteTrack) ─▶ PresenceTracker (line, sessions)
                                                        │
                    TrackingRepository (MongoDB) ◀──────┘
                    latest annotated JPEG  ──────▶  MJPEG stream endpoint
                    live stats             ──────▶  /presence/current, /detections

Heavy CV work never runs on FastAPI's event loop. PyTorch/OpenCV release the
GIL during inference, so the API stays responsive while workers run.
"""
import itertools
import logging
import math
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import cv2
from bson import ObjectId

from app.core.config import settings
from app.core.utils import utcnow
from app.cv.annotate import annotate, encode_jpeg
from app.cv.detector import PersonTracker
from app.cv.line_counter import Line, LineCounter
from app.cv.presence import LineCrossed, PresenceTracker
from app.cv.video_source import VideoSource
from app.services.tracking_service import TrackingRepository
from app.workers.recorder import Recorder

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 5.0
CLEANUP_SECONDS = 3600.0   # how often old recordings are deleted
STREAM_IDLE_SECONDS = 5.0  # stop encoding JPEGs when nobody has watched for this long


class CameraWorker(threading.Thread):
    def __init__(self, camera: dict):
        super().__init__(name=f"camera-{camera['_id']}", daemon=True)
        self.camera_id: ObjectId = camera["_id"]
        self.owner_id: ObjectId = camera["owner_id"]
        self.camera_name: str = camera["name"]
        self.source_type: str = camera["source_type"]
        self.source: str = camera["source"]
        self.line_cfg: dict = camera["line"]
        self.entry_direction: str = camera["entry_direction"]

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._raw_frame = None  # last un-annotated frame, for snapshots
        self._frame_seq = 0
        self._last_stream_request = 0.0

        self._tz = ZoneInfo(settings.TIMEZONE)
        self._recorder: Recorder | None = None
        self.state = "starting"  # starting | running | error | stopped
        self.error: str | None = None
        self.started_at: datetime = utcnow()
        self._stats: dict = {}

    # ------------------------------------------------------------ public API (any thread)

    def stop(self) -> None:
        self._stop_event.set()

    def latest_jpeg(self) -> tuple[int, bytes | None]:
        self._last_stream_request = time.monotonic()
        with self._lock:
            return self._frame_seq, self._jpeg

    def raw_snapshot(self) -> bytes | None:
        with self._lock:
            frame = self._raw_frame
        return encode_jpeg(frame, 85) if frame is not None else None

    def status(self) -> dict:
        with self._lock:
            stats = dict(self._stats)
        return {
            "camera_id": str(self.camera_id),
            "camera_name": self.camera_name,
            "state": self.state,
            "error": self.error,
            "started_at": self.started_at,
            **stats,
        }

    # ------------------------------------------------------------ worker thread

    def run(self) -> None:
        repo = TrackingRepository(self.camera_id, self.owner_id)
        source = VideoSource(self.source_type, self.source)
        presence: PresenceTracker | None = None
        try:
            source.open()
            tracker = PersonTracker()
            w, h = source.width, source.height
            line_px = (
                int(self.line_cfg["x1"] * w), int(self.line_cfg["y1"] * h),
                int(self.line_cfg["x2"] * w), int(self.line_cfg["y2"] * h),
            )
            counter = LineCounter(
                Line(*line_px), self.entry_direction, dead_zone=settings.LINE_DEAD_ZONE * math.hypot(w, h)
            )
            seq = itertools.count(repo.next_person_seq())
            presence = PresenceTracker(
                counter,
                next_person_id=lambda: f"P-{next(seq):04d}",
                min_hits=settings.MIN_TRACK_HITS,
                lost_seconds=settings.TRACK_LOST_SECONDS,
            )

            self.state = "running"
            repo.set_camera_status("running")
            logger.info("Camera %s started (%s, %dx%d @ %.1f fps, device=%s)",
                        self.camera_name, self.source_type, w, h, source.fps, tracker.device)

            if settings.RECORDING_ENABLED:
                self._recorder = Recorder(self.camera_id, self.owner_id, w, h)
            self._loop(source, tracker, presence, counter, repo, line_px)

            self.state = "stopped"
        except Exception as exc:  # noqa: BLE001 - any failure must be reported, not crash silently
            logger.exception("Camera %s failed", self.camera_name)
            self.state = "error"
            self.error = str(exc)
        finally:
            source.release()
            try:
                if self._recorder is not None:
                    self._recorder.close()  # finish the clip in progress
                if presence is not None:
                    repo.handle(presence.close_all())
                if self.state == "error":
                    repo.set_camera_status("error", self.error)
                else:
                    repo.set_camera_status("idle")
            except Exception:  # noqa: BLE001
                logger.exception("Camera %s: failed to persist shutdown state", self.camera_name)

    def _loop(self, source, tracker, presence, counter, repo, line_px) -> None:
        interval = 1.0 / settings.PROCESS_FPS
        play_start = time.monotonic()
        frame_idx = 0
        last_process = 0.0
        next_heartbeat = time.monotonic() + HEARTBEAT_SECONDS
        next_snapshot = time.monotonic()
        fps_ema = 0.0
        recorder = self._recorder
        next_cleanup = time.monotonic()

        while not self._stop_event.is_set():
            if source.is_file:
                # Play files in real time: wait for the next processing slot, then
                # drop any frames that "already happened" while we were busy.
                self._stop_event.wait(max(0.0, last_process + interval - time.monotonic()))
                expected = int((time.monotonic() - play_start) * source.fps)
                if expected > frame_idx:
                    source.skip(expected - frame_idx)
                    frame_idx = expected

            frame = source.read()
            frame_idx += 1

            if source.looped:
                # Video restarted: end everyone's session and reset tracker IDs
                repo.handle(presence.close_all())
                tracker.reset()
                play_start, frame_idx = time.monotonic(), 1

            now_mono = time.monotonic()
            if not source.is_file and now_mono - last_process < interval:
                continue  # live source: read (to drain the buffer) but don't process every frame
            if last_process:
                fps_ema = 0.9 * fps_ema + 0.1 * (1.0 / max(now_mono - last_process, 1e-6))
            last_process = now_mono

            # --- detection + tracking + presence
            people = tracker.track(frame)
            now = utcnow()
            events = presence.update(now, people)
            repo.handle(events)

            visible_ids = {p.track_id for p in people}
            with self._lock:
                self._raw_frame = frame
                self._stats = {
                    "fps": round(fps_ema, 1),
                    "frame_width": source.width,
                    "frame_height": source.height,
                    "in_view": len(presence.in_view),
                    "inside": presence.inside,
                    "entries": counter.entries,
                    "exits": counter.exits,
                    "last_frame_at": now,
                    "recording": bool(recorder and recorder.recording),
                    "people": [
                        {
                            "person_id": st.person_id,
                            "track_id": st.track_id,
                            "first_seen": st.first_seen,
                            "duration_seconds": round((st.last_seen - st.first_seen).total_seconds(), 1),
                            "box": [round(v, 1) for v in st.box],
                        }
                        for st in presence.in_view
                    ],
                }

            # --- annotated frame: needed for recording (always) and the live stream (if watched)
            streaming = now_mono - self._last_stream_request < STREAM_IDLE_SECONDS
            if streaming or recorder:
                img = annotate(
                    frame, line_px, self.entry_direction, list(presence.tracks.values()),
                    len(presence.in_view), presence.inside, counter.entries, counter.exits, visible_ids,
                )
                # timestamp burned into the frame (server TIMEZONE) so recordings are self-describing
                cv2.putText(img, now.astimezone(self._tz).strftime("%Y-%m-%d %H:%M:%S %Z"), (10, img.shape[0] - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                if recorder:
                    crossings = [e for e in events if isinstance(e, LineCrossed)]
                    recorder.on_frame(now, now_mono, img, len(presence.in_view),
                                      [st.person_id for st in presence.in_view], crossings)
                if streaming:
                    if recorder and recorder.recording:
                        img = img.copy()  # the recorder may still hold this frame (poster)
                        cv2.circle(img, (img.shape[1] - 70, 22), 6, (0, 0, 230), -1)
                        cv2.putText(img, "REC", (img.shape[1] - 58, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                    (255, 255, 255), 1, cv2.LINE_AA)
                    jpeg = encode_jpeg(img, settings.STREAM_JPEG_QUALITY)
                    with self._lock:
                        self._jpeg = jpeg
                        self._frame_seq += 1

            # --- periodic DB writes
            if now_mono >= next_heartbeat:
                repo.heartbeat(presence.active_sessions())
                next_heartbeat = now_mono + HEARTBEAT_SECONDS
            if recorder and now_mono >= next_cleanup:
                recorder.store.cleanup()
                next_cleanup = now_mono + CLEANUP_SECONDS
            if now_mono >= next_snapshot:
                repo.snapshot(now, len(presence.in_view), presence.inside, counter.entries, counter.exits)
                next_snapshot = now_mono + settings.SNAPSHOT_INTERVAL_SECONDS
