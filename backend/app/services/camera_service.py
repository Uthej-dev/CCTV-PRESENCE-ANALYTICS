import asyncio

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.utils import to_object_id, utcnow
from app.database.indexes import CAMERAS, EVENTS, OCCUPANCY, RECORDINGS, TRACKING_SESSIONS
from app.database.mongodb import get_db
from app.schemas.camera import CameraCreate, CameraOut, CameraStatus, CameraUpdate, validate_source
from app.cv.annotate import encode_jpeg
from app.cv.video_source import VideoSource, VideoSourceError
from app.services.recording_service import delete_camera_media
from app.workers.camera_worker import CameraWorker
from app.workers.manager import manager

# Changing any of these on a running camera restarts its worker
RESTART_FIELDS = {"source_type", "source", "line", "entry_direction", "name"}


def to_camera_out(doc: dict) -> CameraOut:
    return CameraOut(id=str(doc["_id"]), **{k: v for k, v in doc.items() if k not in ("_id", "owner_id")})


async def list_cameras(owner_id: ObjectId) -> list[dict]:
    cursor = get_db()[CAMERAS].find({"owner_id": owner_id}).sort("created_at", 1)
    return await cursor.to_list()


async def get_camera(owner_id: ObjectId, camera_id: str) -> dict:
    oid = to_object_id(camera_id)
    doc = await get_db()[CAMERAS].find_one({"_id": oid, "owner_id": owner_id}) if oid else None
    if doc is None:
        raise NotFoundError("Camera not found")
    return doc


async def create_camera(owner_id: ObjectId, data: CameraCreate) -> dict:
    now = utcnow()
    doc = {
        **data.model_dump(mode="json"),
        "owner_id": owner_id,
        "status": CameraStatus.IDLE.value,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await get_db()[CAMERAS].insert_one(doc)
    except DuplicateKeyError:
        raise ConflictError(f"A camera named '{data.name}' already exists")
    doc["_id"] = result.inserted_id
    return doc


async def update_camera(owner_id: ObjectId, camera_id: str, data: CameraUpdate) -> dict:
    current = await get_camera(owner_id, camera_id)
    changes = data.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    if not changes:
        return current

    # Validate the merged source config (type and value may be updated independently)
    try:
        validate_source(changes.get("source_type", current["source_type"]), changes.get("source", current["source"]))
    except ValueError as e:
        raise ValidationError(str(e))

    changes["updated_at"] = utcnow()
    try:
        updated = await get_db()[CAMERAS].find_one_and_update(
            {"_id": current["_id"], "owner_id": owner_id},
            {"$set": changes},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise ConflictError(f"A camera named '{changes.get('name')}' already exists")

    # Keep a running worker consistent with the new config
    cid = str(updated["_id"])
    if manager.is_running(cid):
        if not updated["is_active"]:
            await asyncio.to_thread(manager.stop, cid)
        elif RESTART_FIELDS & changes.keys():
            await asyncio.to_thread(manager.stop, cid)
            manager.start(updated)
        updated = await get_db()[CAMERAS].find_one({"_id": updated["_id"]})
    return updated


async def delete_camera(owner_id: ObjectId, camera_id: str) -> None:
    camera = await get_camera(owner_id, camera_id)
    await asyncio.to_thread(manager.stop, str(camera["_id"]))
    db = get_db()
    await db[CAMERAS].delete_one({"_id": camera["_id"]})
    # Cascade: remove the camera's recorded data
    for coll in (TRACKING_SESSIONS, EVENTS, OCCUPANCY, RECORDINGS):
        await db[coll].delete_many({"camera_id": camera["_id"]})
    await asyncio.to_thread(delete_camera_media, camera["_id"])


async def start_camera(owner_id: ObjectId, camera_id: str) -> CameraWorker:
    camera = await get_camera(owner_id, camera_id)
    if not camera["is_active"]:
        raise ValidationError("Camera is deactivated; activate it before starting")
    return manager.start(camera)


async def stop_camera(owner_id: ObjectId, camera_id: str) -> None:
    camera = await get_camera(owner_id, camera_id)
    cid = str(camera["_id"])
    await asyncio.to_thread(manager.stop, cid)
    # The worker resets its own status on exit; this also clears a stale "running"
    # left behind if the worker had already died.
    await get_db()[CAMERAS].update_one(
        {"_id": camera["_id"], "status": CameraStatus.RUNNING.value},
        {"$set": {"status": CameraStatus.IDLE.value, "updated_at": utcnow()}},
    )


def _grab_frame(source_type: str, source: str) -> bytes:
    src = VideoSource(source_type, source)
    try:
        src.open()
        return encode_jpeg(src.read(), 85)
    finally:
        src.release()


async def get_snapshot(owner_id: ObjectId, camera_id: str) -> bytes:
    """One raw (un-annotated) JPEG frame: from the running worker, or read directly from the source."""
    camera = await get_camera(owner_id, camera_id)
    worker = manager.get(str(camera["_id"]))
    if worker is not None and worker.is_alive():
        for _ in range(30):  # a just-started worker may not have processed a frame yet
            jpeg = await asyncio.to_thread(worker.raw_snapshot)
            if jpeg:
                return jpeg
            await asyncio.sleep(0.1)
    try:
        return await asyncio.to_thread(_grab_frame, camera["source_type"], camera["source"])
    except VideoSourceError as e:
        raise ValidationError(str(e))
