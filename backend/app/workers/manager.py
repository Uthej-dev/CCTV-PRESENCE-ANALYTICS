"""Keeps track of running camera workers (one thread per camera)."""
import logging
import threading

from app.core.config import settings
from app.core.exceptions import ConflictError, ValidationError
from app.cv.video_source import file_exists
from app.workers.camera_worker import CameraWorker

logger = logging.getLogger(__name__)


class WorkerManager:
    def __init__(self):
        self._workers: dict[str, CameraWorker] = {}
        self._lock = threading.Lock()

    def _prune(self) -> None:
        for cid, w in list(self._workers.items()):
            if not w.is_alive():
                del self._workers[cid]

    def get(self, camera_id: str) -> CameraWorker | None:
        """Return the worker for a camera; finished/crashed workers are kept so their error can be read."""
        with self._lock:
            return self._workers.get(camera_id)

    def is_running(self, camera_id: str) -> bool:
        w = self.get(camera_id)
        return w is not None and w.is_alive()

    def running(self) -> list[CameraWorker]:
        with self._lock:
            return [w for w in self._workers.values() if w.is_alive()]

    def start(self, camera: dict) -> CameraWorker:
        cid = str(camera["_id"])
        if camera["source_type"] == "file" and not file_exists(camera["source"]):
            raise ValidationError(f"Video file not found: {camera['source']} (looked in '{settings.VIDEO_DIR}/')")

        with self._lock:
            existing = self._workers.get(cid)
            if existing is not None and existing.is_alive():
                return existing
            self._prune()
            if len(self._workers) >= settings.MAX_RUNNING_CAMERAS:
                raise ConflictError(f"At most {settings.MAX_RUNNING_CAMERAS} cameras can run at the same time")
            worker = CameraWorker(camera)
            self._workers[cid] = worker
            worker.start()
            return worker

    def stop(self, camera_id: str, timeout: float = 10.0) -> None:
        """Blocking: call from a thread (asyncio.to_thread) in async code."""
        with self._lock:
            worker = self._workers.pop(camera_id, None)
        if worker is not None:
            worker.stop()
            worker.join(timeout)
            if worker.is_alive():
                logger.warning("Camera worker %s did not stop within %.0fs", camera_id, timeout)

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self._workers)
        for cid in ids:
            self.stop(cid)


manager = WorkerManager()
