"""Collection names and index definitions.

Collections
-----------
users               one doc per account
cameras             camera config + runtime status, owned by a user
tracking_sessions   one doc per tracked person per visit (entry -> exit, duration)
events              entry / exit line-crossing events (append-only log)
occupancy_snapshots periodic occupancy samples per camera (for time-series charts)
recordings          video clips recorded while people were in view (MP4 files in MEDIA_DIR, metadata here)

Analytics (daily / weekly / peak hour) are computed with aggregation pipelines
over `events`, `tracking_sessions` and `occupancy_snapshots`, so there is no
separate pre-aggregated analytics collection in the MVP.
"""
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings

USERS = "users"
CAMERAS = "cameras"
TRACKING_SESSIONS = "tracking_sessions"
EVENTS = "events"
OCCUPANCY = "occupancy_snapshots"
RECORDINGS = "recordings"

INDEXES: dict[str, list[IndexModel]] = {
    USERS: [
        IndexModel([("email", ASCENDING)], unique=True, name="uniq_email"),
    ],
    CAMERAS: [
        IndexModel([("owner_id", ASCENDING), ("name", ASCENDING)], unique=True, name="uniq_owner_name"),
    ],
    TRACKING_SESSIONS: [
        IndexModel([("camera_id", ASCENDING), ("entry_time", DESCENDING)], name="camera_entry_time"),
        IndexModel([("camera_id", ASCENDING), ("status", ASCENDING)], name="camera_status"),
        IndexModel([("owner_id", ASCENDING), ("entry_time", DESCENDING)], name="owner_entry_time"),
    ],
    EVENTS: [
        IndexModel([("camera_id", ASCENDING), ("timestamp", DESCENDING)], name="camera_timestamp"),
        IndexModel([("owner_id", ASCENDING), ("timestamp", DESCENDING)], name="owner_timestamp"),
    ],
    OCCUPANCY: [
        IndexModel([("camera_id", ASCENDING), ("timestamp", DESCENDING)], name="camera_timestamp"),
        IndexModel([("owner_id", ASCENDING), ("timestamp", DESCENDING)], name="owner_timestamp"),
        # TTL: MongoDB deletes samples automatically after the retention period
        IndexModel([("timestamp", ASCENDING)], name="ttl_timestamp",
                   expireAfterSeconds=settings.SNAPSHOT_RETENTION_DAYS * 86400),
    ],
    RECORDINGS: [
        IndexModel([("camera_id", ASCENDING), ("start_time", DESCENDING)], name="camera_start"),
        IndexModel([("owner_id", ASCENDING), ("start_time", DESCENDING)], name="owner_start"),
        IndexModel([("camera_id", ASCENDING), ("person_ids", ASCENDING)], name="camera_person"),
        # Metadata expires with the files (files are removed by RecordingStore.cleanup)
        IndexModel([("start_time", ASCENDING)], name="ttl_start",
                   expireAfterSeconds=settings.RECORDING_RETENTION_DAYS * 86400),
    ],
}


async def create_indexes(db: AsyncDatabase) -> None:
    for collection, indexes in INDEXES.items():
        await db[collection].create_indexes(indexes)
