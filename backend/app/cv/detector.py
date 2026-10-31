"""YOLO person detection + ByteTrack tracking (Ultralytics built-in tracker)."""
import threading
from contextlib import nullcontext
from dataclasses import dataclass

import numpy as np
import torch
from ultralytics import YOLO

from app.core.config import settings

PERSON_CLASS_ID = 0  # COCO class 0 = person

# PyTorch's Apple-GPU (MPS) backend is not thread-safe: two camera threads running
# inference at the same time crash the process. GPU inference is therefore
# serialised; it is fast (~12 ms/frame), so several cameras still fit in real time.
_GPU_LOCK = threading.Lock()


@dataclass
class TrackedPerson:
    track_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float

    @property
    def anchor(self) -> tuple[float, float]:
        """Bottom-centre of the box (approximately where the person stands)."""
        return (self.x1 + self.x2) / 2, self.y2


def pick_device() -> str:
    if settings.YOLO_DEVICE:
        return settings.YOLO_DEVICE
    if torch.cuda.is_available():
        return "cuda:0"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class PersonTracker:
    """One instance per camera: ByteTrack keeps its state inside the model's predictor."""

    def __init__(self):
        self.model = YOLO(settings.YOLO_MODEL)
        self.device = pick_device()

    def track(self, frame: np.ndarray) -> list[TrackedPerson]:
        with _GPU_LOCK if self.device == "mps" else nullcontext():
            return self._track(frame)

    def _track(self, frame: np.ndarray) -> list[TrackedPerson]:
        result = self.model.track(
            frame,
            persist=True,               # keep track IDs between calls
            classes=[PERSON_CLASS_ID],
            conf=settings.DETECTION_CONFIDENCE,
            tracker="bytetrack.yaml",
            device=self.device,
            verbose=False,
        )[0]

        boxes = result.boxes
        if boxes is None or boxes.id is None:
            return []
        xyxy = boxes.xyxy.cpu().numpy()
        ids = boxes.id.int().cpu().tolist()
        confs = boxes.conf.cpu().tolist()
        return [
            TrackedPerson(track_id=tid, x1=b[0], y1=b[1], x2=b[2], y2=b[3], confidence=c)
            for tid, b, c in zip(ids, xyxy.tolist(), confs)
        ]

    def reset(self) -> None:
        """Clear tracker state (e.g. when a video file loops back to the start)."""
        predictor = getattr(self.model, "predictor", None)
        for tracker in getattr(predictor, "trackers", None) or []:
            tracker.reset()
