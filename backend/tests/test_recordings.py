import time
from datetime import datetime, timedelta, timezone

import numpy as np
from bson import ObjectId

from app.cv.clip_writer import ClipWriter
from app.services.recording_service import RecordingStore, camera_media_dir
from tests.conftest import needs_sample_video, register

T0 = datetime(2026, 3, 10, 10, 0, 0, tzinfo=timezone.utc)


def setup_camera(client, headers, name="Door"):
    owner = ObjectId(client.get("/auth/me", headers=headers).json()["id"])
    cam = client.post("/cameras", json={"name": name, "source": "people-detection.mp4"}, headers=headers).json()
    return owner, ObjectId(cam["id"])


def token(headers):
    return headers["Authorization"].split()[1]


def make_clip(store, start, seconds, max_people, person_ids, events=()):
    """Write a real (tiny) MP4 + poster through the same code path the worker uses."""
    clip_id, path = store.new_clip(start)
    w = ClipWriter(path, (64, 64), fps=5, start_mono=0.0)
    frame = np.zeros((64, 64, 3), np.uint8)
    for i in range(int(seconds * 5)):
        w.write(frame, i / 5)
    assert w.close()
    path.with_suffix(".jpg").write_bytes(b"\xff\xd8poster\xff\xd9")
    store.complete(clip_id, {
        "end_time": start + timedelta(seconds=w.duration), "duration_seconds": w.duration,
        "max_people": max_people, "person_ids": person_ids, "entries": 1, "exits": 0,
        "marks": [{"offset": 0.0, "in_view": max_people}], "events": list(events),
        "size_bytes": path.stat().st_size,
    })
    return str(clip_id)


def test_list_filter_and_lookup_by_time(client, auth_headers):
    owner, cam = setup_camera(client, auth_headers)
    store = RecordingStore(cam, owner)
    make_clip(store, T0, 4, 1, ["P-0001"])
    busy = make_clip(store, T0 + timedelta(minutes=10), 6, 3, ["P-0002", "P-0003", "P-0004"],
                     events=[{"offset": 1.0, "type": "entry", "person_id": "P-0002"}])

    page = client.get("/recordings", headers=auth_headers).json()
    assert page["total"] == 2 and page["items"][0]["id"] == busy  # newest first
    assert page["items"][0]["events"][0]["type"] == "entry"

    assert client.get("/recordings?min_people=2", headers=auth_headers).json()["total"] == 1
    assert client.get("/recordings?person_id=P-0001", headers=auth_headers).json()["total"] == 1
    # overlap: a window inside the first clip finds it
    window = {"start": (T0 + timedelta(seconds=1)).isoformat(), "end": (T0 + timedelta(seconds=2)).isoformat()}
    assert client.get("/recordings", params=window, headers=auth_headers).json()["total"] == 1

    at = client.get("/recordings/at", params={"at": (T0 + timedelta(minutes=10, seconds=3)).isoformat()},
                    headers=auth_headers).json()
    assert at["recording"]["id"] == busy and at["offset_seconds"] == 3.0
    missing = client.get("/recordings/at", params={"at": (T0 + timedelta(hours=5)).isoformat()}, headers=auth_headers)
    assert missing.status_code == 404


def test_video_is_served_with_range_support(client, auth_headers):
    owner, cam = setup_camera(client, auth_headers)
    clip = make_clip(RecordingStore(cam, owner), T0, 4, 1, ["P-0001"])
    url = f"/recordings/{clip}/video?token={token(auth_headers)}"
    full = client.get(url)
    assert full.status_code == 200 and full.headers["content-type"] == "video/mp4"
    part = client.get(url, headers={"Range": "bytes=0-99"})
    assert part.status_code == 206 and len(part.content) == 100   # browsers need this to seek
    assert client.get(f"/recordings/{clip}/poster?token={token(auth_headers)}").status_code == 200


def test_recordings_are_private(client, auth_headers):
    owner, cam = setup_camera(client, auth_headers)
    clip = make_clip(RecordingStore(cam, owner), T0, 2, 1, [])
    bob = register(client, email="bob@example.com").json()["access_token"]
    assert client.get("/recordings", headers={"Authorization": f"Bearer {bob}"}).json()["total"] == 0
    assert client.get(f"/recordings/{clip}/video?token={bob}").status_code == 404
    assert client.delete(f"/recordings/{clip}", headers={"Authorization": f"Bearer {bob}"}).status_code == 404


def test_delete_recording_and_camera_cascade(client, auth_headers):
    owner, cam = setup_camera(client, auth_headers)
    store = RecordingStore(cam, owner)
    a = make_clip(store, T0, 2, 1, [])
    make_clip(store, T0 + timedelta(minutes=1), 2, 1, [])
    assert client.delete(f"/recordings/{a}", headers=auth_headers).status_code == 204
    assert client.get("/recordings", headers=auth_headers).json()["total"] == 1
    client.delete(f"/cameras/{cam}", headers=auth_headers)
    assert not camera_media_dir(cam).exists()
    assert client.get("/recordings", headers=auth_headers).json()["total"] == 0


def test_cleanup_and_unfinished_clips(client, auth_headers):
    owner, cam = setup_camera(client, auth_headers)
    store = RecordingStore(cam, owner)
    make_clip(store, T0 - timedelta(days=30), 2, 1, [])
    make_clip(store, T0, 2, 1, [])
    assert store.cleanup(now=T0) == 1

    # a clip left "recording" by a crash is removed at startup
    _, path = store.new_clip(T0 + timedelta(minutes=5))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"truncated")
    from app.services.recording_service import discard_unfinished
    client.portal.call(discard_unfinished)  # run on the app's event loop (where the DB client lives)
    assert not path.exists()
    assert all(r["status"] == "complete" for r in client.get("/recordings", headers=auth_headers).json()["items"])


@needs_sample_video
def test_running_camera_records_playable_clip(client, auth_headers):
    """End to end: worker on the sample video -> YOLO -> tracking -> recorder -> H.264 MP4."""
    _, cam = setup_camera(client, auth_headers)
    assert client.post(f"/cameras/{cam}/start", headers=auth_headers).status_code == 202
    try:
        deadline = time.time() + 60
        done = []
        while time.time() < deadline and not done:
            time.sleep(1)
            items = client.get(f"/recordings?camera_id={cam}", headers=auth_headers).json()["items"]
            done = [r for r in items if r["status"] == "complete"]
        assert done, "no clip completed"
        clip = done[-1]
        assert clip["duration_seconds"] > 1 and clip["max_people"] >= 1 and clip["person_ids"]
        assert clip["marks"][0]["in_view"] == 0  # starts with pre-roll (before the person appeared)
        video = client.get(f"/recordings/{clip['id']}/video?token={token(auth_headers)}")
        assert video.status_code == 200 and video.content[4:8] == b"ftyp"  # MP4 container
    finally:
        client.post(f"/cameras/{cam}/stop", headers=auth_headers)
