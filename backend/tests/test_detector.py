import threading

import pytest
import torch

from tests.conftest import SAMPLE_VIDEO, needs_sample_video


@needs_sample_video
@pytest.mark.skipif(not torch.backends.mps.is_available(), reason="Apple-GPU specific regression")
def test_parallel_trackers_on_mps_do_not_crash():
    """Several camera threads used to crash the process on MPS (Metal command buffer assertion)."""
    import cv2

    from app.cv.detector import PersonTracker

    cap = cv2.VideoCapture(SAMPLE_VIDEO)
    frames = [cap.read()[1] for _ in range(20)]
    done = []

    def run():
        t = PersonTracker()
        for f in frames:
            t.track(f)
        done.append(True)

    threads = [threading.Thread(target=run) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert len(done) == 3


@needs_sample_video
def test_detects_people_in_sample_video():
    import cv2

    from app.cv.detector import PersonTracker

    cap = cv2.VideoCapture(SAMPLE_VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 357)  # frame with three people walking
    tracker = PersonTracker()
    people = []
    for _ in range(5):
        people = tracker.track(cap.read()[1])
    assert len(people) >= 2
    assert all(p.track_id > 0 for p in people)
