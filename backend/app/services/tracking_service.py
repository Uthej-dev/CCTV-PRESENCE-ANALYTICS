"""Persistence of tracking sessions, entry/exit events and occupancy snapshots.

Write side (sync, called from camera worker threads) and read side (async,
called from API routes) live together because they share the document shapes.

tracking_sessions
    {camera_id, owner_id, person_id: "P-0001", track_id, status: active|closed,
     first_seen, last_seen, duration_seconds, entry_time, exit_time}
events
    {camera_id, owner_id, session_id, person_id, track_id, type: entry|exit, timestamp}
occupancy_snapshots
    {camera_id, owner_id, timestamp, in_view, inside, entries, exits}
"""
from datetime import datetime

from bson import ObjectId
from pymongo import UpdateOne

from app.core.utils import utcnow
from app.cv.presence import LineCrossed, SessionEnded, SessionStarted, TrackState
from app.database.indexes import CAMERAS, EVENTS, OCCUPANCY, TRACKING_SESSIONS
from app.database.mongodb import get_db
from app.database.sync_mongodb import get_sync_db


# ---------------------------------------------------------------- write side (sync)

class TrackingRepository:
    """Used by one camera worker to persist what its PresenceTracker produces."""

    def __init__(self, camera_id: ObjectId, owner_id: ObjectId):
        self.camera_id = camera_id
        self.owner_id = owner_id
        self.db = get_sync_db()
        self._session_ids: dict[str, ObjectId] = {}  # person_id -> session _id

    def next_person_seq(self) -> int:
        """Next free person number for this camera (labels stay unique across restarts)."""
        return self.db[TRACKING_SESSIONS].count_documents({"camera_id": self.camera_id}) + 1

    def session_started(self, e: SessionStarted) -> None:
        result = self.db[TRACKING_SESSIONS].insert_one({
            "camera_id": self.camera_id,
            "owner_id": self.owner_id,
            "person_id": e.person_id,
            "track_id": e.track_id,
            "status": "active",
            "first_seen": e.first_seen,
            "last_seen": e.first_seen,
            "duration_seconds": 0.0,
            "entry_time": None,
            "exit_time": None,
        })
        self._session_ids[e.person_id] = result.inserted_id

    def line_crossed(self, e: LineCrossed) -> None:
        session_id = self._session_ids.get(e.person_id)
        self.db[EVENTS].insert_one({
            "camera_id": self.camera_id,
            "owner_id": self.owner_id,
            "session_id": session_id,
            "person_id": e.person_id,
            "track_id": e.track_id,
            "type": e.type,
            "timestamp": e.timestamp,
        })
        if session_id:
            field = "entry_time" if e.type == "entry" else "exit_time"
            self.db[TRACKING_SESSIONS].update_one({"_id": session_id}, {"$set": {field: e.timestamp}})

    def session_ended(self, e: SessionEnded) -> None:
        session_id = self._session_ids.pop(e.person_id, None)
        if session_id is None:
            return
        self.db[TRACKING_SESSIONS].update_one(
            {"_id": session_id},
            {"$set": {
                "status": "closed",
                "last_seen": e.last_seen,
                "duration_seconds": round(e.duration_seconds, 2),
            }},
        )

    def handle(self, events) -> None:
        for e in events:
            if isinstance(e, SessionStarted):
                self.session_started(e)
            elif isinstance(e, LineCrossed):
                self.line_crossed(e)
            elif isinstance(e, SessionEnded):
                self.session_ended(e)

    def heartbeat(self, active: list[TrackState]) -> None:
        """Refresh last_seen / duration of open sessions so the API sees live values."""
        ops = [
            UpdateOne(
                {"_id": self._session_ids[st.person_id]},
                {"$set": {
                    "last_seen": st.last_seen,
                    "duration_seconds": round((st.last_seen - st.first_seen).total_seconds(), 2),
                }},
            )
            for st in active
            if st.person_id in self._session_ids
        ]
        if ops:
            self.db[TRACKING_SESSIONS].bulk_write(ops, ordered=False)

    def snapshot(self, timestamp: datetime, in_view: int, inside: int, entries: int, exits: int) -> None:
        self.db[OCCUPANCY].insert_one({
            "camera_id": self.camera_id,
            "owner_id": self.owner_id,
            "timestamp": timestamp,
            "in_view": in_view,
            "inside": inside,
            "entries": entries,
            "exits": exits,
        })

    def set_camera_status(self, status: str, error: str | None = None) -> None:
        self.db[CAMERAS].update_one(
            {"_id": self.camera_id},
            {"$set": {"status": status, "last_error": error, "updated_at": utcnow()}},
        )


# ---------------------------------------------------------------- startup cleanup (async)

async def recover_after_restart() -> None:
    """A previous server process may have died mid-run: reset stale state."""
    db = get_db()
    await db[CAMERAS].update_many({"status": "running"}, {"$set": {"status": "idle"}})
    await db[TRACKING_SESSIONS].update_many({"status": "active"}, {"$set": {"status": "closed"}})
    from app.services.recording_service import discard_unfinished  # local import avoids a cycle
    await discard_unfinished()


# ---------------------------------------------------------------- read side (async)

def _camera_filter(owner_id: ObjectId, camera_id: ObjectId | None) -> dict:
    q: dict = {"owner_id": owner_id}
    if camera_id is not None:
        q["camera_id"] = camera_id
    return q


def _time_range(field: str, start: datetime | None, end: datetime | None) -> dict:
    rng = {}
    if start:
        rng["$gte"] = start
    if end:
        rng["$lt"] = end
    return {field: rng} if rng else {}


async def list_sessions(
    owner_id: ObjectId,
    camera_id: ObjectId | None = None,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    q = {**_camera_filter(owner_id, camera_id), **_time_range("first_seen", start, end)}
    if status:
        q["status"] = status
    coll = get_db()[TRACKING_SESSIONS]
    total = await coll.count_documents(q)
    docs = await coll.find(q).sort("first_seen", -1).skip(skip).limit(limit).to_list()
    return docs, total


async def list_events(
    owner_id: ObjectId,
    camera_id: ObjectId | None = None,
    event_type: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    q = {**_camera_filter(owner_id, camera_id), **_time_range("timestamp", start, end)}
    if event_type:
        q["type"] = event_type
    coll = get_db()[EVENTS]
    total = await coll.count_documents(q)
    docs = await coll.find(q).sort("timestamp", -1).skip(skip).limit(limit).to_list()
    return docs, total
