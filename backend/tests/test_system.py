import io
import os

import pytest

from app.core.config import Settings
from tests.conftest import needs_sample_video


@needs_sample_video
def test_videos_list_includes_samples(client, auth_headers):
    names = [v["name"] for v in client.get("/videos", headers=auth_headers).json()]
    assert "people-detection.mp4" in names


def test_upload_rejects_wrong_type_and_garbage(client, auth_headers):
    res = client.post("/videos", files={"file": ("notes.txt", b"hello", "text/plain")}, headers=auth_headers)
    assert res.status_code == 422
    res = client.post("/videos", files={"file": ("fake.mp4", b"not a video", "video/mp4")}, headers=auth_headers)
    assert res.status_code == 422
    assert not os.path.exists("videos/fake.mp4")


@needs_sample_video
def test_upload_real_video_then_conflict(client, auth_headers):
    data = open("videos/people-detection.mp4", "rb").read()
    try:
        res = client.post("/videos", files={"file": ("My Clip!.mp4", io.BytesIO(data), "video/mp4")},
                          headers=auth_headers)
        assert res.status_code == 201
        assert res.json()["name"] == "My-Clip.mp4"
        res = client.post("/videos", files={"file": ("My Clip!.mp4", io.BytesIO(data), "video/mp4")},
                          headers=auth_headers)
        assert res.status_code == 409
    finally:
        if os.path.exists("videos/My-Clip.mp4"):
            os.remove("videos/My-Clip.mp4")


def test_system_info(client, auth_headers):
    info = client.get("/system/info", headers=auth_headers).json()
    assert info["yolo_device"] in ("cpu", "mps", "cuda:0")


def test_production_requires_strong_secret():
    with pytest.raises(ValueError):
        Settings(ENVIRONMENT="production", JWT_SECRET="change-me")
    Settings(ENVIRONMENT="production", JWT_SECRET="x" * 40)
