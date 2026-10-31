"""Video recordings: MP4 clips recorded while people are in view.

Files:     MEDIA_DIR/recordings/<camera_id>/<YYYY-MM-DD>/<HHMMSS>_<id>.mp4   (+ .jpg poster)
Metadata:  `recordings` collection
    {camera_id, owner_id, status: recording|complete, start_time, end_time, duration_seconds,
     max_people, person_ids, entries, exits,
     marks:  [{offset, in_view}]            people-count changes, seconds into the clip
     events: [{offset, type, person_id}]    line crossings, seconds into the clip
     path, poster_path, size_bytes}

Video files stay on disk, not in MongoDB: clips are megabytes each.
"""
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from bson import ObjectId

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.utils import to_object_id, utcnow
from app.database.indexes import RECORDINGS
from app.database.mongodb import get_db
from app.database.sync_mongodb import get_sync_db

SUBDIR = "recordings"


def media_dir() -> Path:
    return Path(settings.MEDIA_DIR).resolve()


def camera_media_dir(camera_id: ObjectId) -> Path:
    return media_dir() / SUBDIR / str(camera_id)


# ---------------------------------------------------------------- write side (sync, worker threads)

class RecordingStore:
    def __init__(self, camera_id: ObjectId, owner_id: ObjectId):
        self.camera_id = camera_id
        self.owner_id = owner_id
        self.db = get_sync_db()

    def new_clip(self, start_time: datetime) -> tuple[ObjectId, Path]:
        """Create the DB doc for a clip that is starting; returns (id, absolute mp4 path)."""
        clip_id = ObjectId()
        rel = Path(SUBDIR) / str(self.camera_id) / start_time.strftime("%Y-%m-%d") / f"{start_time:%H%M%S}_{clip_id}.mp4"
        self.db[RECORDINGS].insert_one({
            "_id": clip_id,
            "camera_id": self.camera_id,
            "owner_id": self.owner_id,
            "status": "recording",
            "start_time": start_time,
            "end_time": start_time,
            "duration_seconds": 0.0,
            "max_people": 0,
            "person_ids": [],
            "entries": 0,
            "exits": 0,
            "marks": [],
            "events": [],
            "path": rel.as_posix(),
            "poster_path": rel.with_suffix(".jpg").as_posix(),
            "size_bytes": 0,
        })
        return clip_id, media_dir() / rel

    def complete(self, clip_id: ObjectId, fields: dict) -> None:
        self.db[RECORDINGS].update_one({"_id": clip_id}, {"$set": {**fields, "status": "complete"}})

    def discard(self, clip_id: ObjectId, path: Path) -> None:
        self.db[RECORDINGS].delete_one({"_id": clip_id})
        path.unlink(missing_ok=True)
        path.with_suffix(".jpg").unlink(missing_ok=True)

    def cleanup(self, now: datetime | None = None) -> int:
        """Delete day folders older than the retention period. Returns folders removed."""
        cutoff = ((now or utcnow()) - timedelta(days=settings.RECORDING_RETENTION_DAYS)).strftime("%Y-%m-%d")
        base = camera_media_dir(self.camera_id)
        removed = 0
        if base.is_dir():
            for day in base.iterdir():
                if day.is_dir() and day.name < cutoff:
                    shutil.rmtree(day, ignore_errors=True)
                    removed += 1
        return removed


def delete_camera_media(camera_id: ObjectId) -> None:
    shutil.rmtree(camera_media_dir(camera_id), ignore_errors=True)


async def discard_unfinished() -> None:
    """Clips still 'recording' after a restart were cut off mid-write and aren't playable."""
    db = get_db()
    async for doc in db[RECORDINGS].find({"status": "recording"}):
        (media_dir() / doc["path"]).unlink(missing_ok=True)
        (media_dir() / doc["poster_path"]).unlink(missing_ok=True)
        await db[RECORDINGS].delete_one({"_id": doc["_id"]})


# ---------------------------------------------------------------- read side (async, API)

def _query(owner_id, camera_id, start, end, min_people, person_id) -> dict:
    q: dict = {"owner_id": owner_id}
    if camera_id is not None:
        q["camera_id"] = camera_id
    # clips OVERLAPPING [start, end)
    if end:
        q["start_time"] = {"$lt": end}
    if start:
        q["end_time"] = {"$gte": start}
    if min_people:
        q["max_people"] = {"$gte": min_people}
    if person_id:
        q["person_ids"] = person_id
    return q


async def list_recordings(owner_id, camera_id=None, start=None, end=None, min_people=None, person_id=None,
                          skip=0, limit=24, oldest_first=False) -> tuple[list[dict], int]:
    q = _query(owner_id, camera_id, start, end, min_people, person_id)
    coll = get_db()[RECORDINGS]
    total = await coll.count_documents(q)
    docs = await coll.find(q).sort("start_time", 1 if oldest_first else -1).skip(skip).limit(limit).to_list()
    return docs, total


async def recording_at(owner_id, at: datetime, camera_id=None, slack_seconds: float = 120) -> tuple[dict, float]:
    """The clip covering time `at` (or the nearest one within `slack_seconds`) and the offset to seek to."""
    q = _query(owner_id, camera_id, at - timedelta(seconds=slack_seconds), at + timedelta(seconds=slack_seconds),
               None, None)
    docs = await get_db()[RECORDINGS].find({**q, "status": "complete"}).to_list()
    if not docs:
        raise NotFoundError("No recording around that time")

    def distance(d):
        if d["start_time"] <= at <= d["end_time"]:
            return 0.0
        return min(abs((d["start_time"] - at).total_seconds()), abs((d["end_time"] - at).total_seconds()))

    doc = min(docs, key=distance)
    offset = (at - doc["start_time"]).total_seconds()
    return doc, max(0.0, min(offset, doc["duration_seconds"]))


async def get_recording(owner_id: ObjectId, recording_id: str) -> dict:
    oid = to_object_id(recording_id)
    doc = await get_db()[RECORDINGS].find_one({"_id": oid, "owner_id": owner_id}) if oid else None
    if doc is None:
        raise NotFoundError("Recording not found")
    return doc


def file_path(doc: dict, key: str) -> Path:
    base = media_dir()
    path = (base / doc[key]).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise NotFoundError("Recording file not available" + (" yet (still recording)" if doc["status"] == "recording" else ""))
    return path


async def delete_recording(owner_id: ObjectId, recording_id: str) -> None:
    doc = await get_recording(owner_id, recording_id)
    for key in ("path", "poster_path"):
        (media_dir() / doc[key]).unlink(missing_ok=True)
    await get_db()[RECORDINGS].delete_one({"_id": doc["_id"]})
