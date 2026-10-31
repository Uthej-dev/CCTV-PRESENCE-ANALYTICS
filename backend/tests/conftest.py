import os

import tempfile

# Must be set before the app (and its settings) are imported
os.environ["MONGODB_DB"] = "cctv_analytics_test"
os.environ["MEDIA_DIR"] = tempfile.mkdtemp(prefix="cctv-test-media-")
os.environ["RECORDING_POST_ROLL_SECONDS"] = "1"  # short clips keep the end-to-end test fast

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def clean_db():
    sync = MongoClient(settings.MONGODB_URI)
    sync.drop_database(settings.MONGODB_DB)
    yield
    sync.drop_database(settings.MONGODB_DB)
    sync.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


SAMPLE_VIDEO = os.path.join(settings.VIDEO_DIR, "people-detection.mp4")
needs_sample_video = pytest.mark.skipif(
    not os.path.exists(SAMPLE_VIDEO), reason="run scripts/download_samples.py first"
)


def register(client, email="alice@example.com", password="password123", full_name="Alice"):
    return client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})


@pytest.fixture
def auth_headers(client):
    token = register(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
