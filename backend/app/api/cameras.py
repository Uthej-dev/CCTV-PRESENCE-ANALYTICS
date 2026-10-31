import asyncio

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, get_current_user_from_query
from app.core.exceptions import ConflictError
from app.schemas.camera import CameraCreate, CameraOut, CameraUpdate
from app.schemas.detection import CameraLiveStatus
from app.services import camera_service
from app.workers.manager import manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
async def list_cameras(user: dict = Depends(get_current_user)):
    docs = await camera_service.list_cameras(user["_id"])
    return [camera_service.to_camera_out(d) for d in docs]


@router.post("", response_model=CameraOut, status_code=status.HTTP_201_CREATED)
async def create_camera(data: CameraCreate, user: dict = Depends(get_current_user)):
    doc = await camera_service.create_camera(user["_id"], data)
    return camera_service.to_camera_out(doc)


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(camera_id: str, user: dict = Depends(get_current_user)):
    doc = await camera_service.get_camera(user["_id"], camera_id)
    return camera_service.to_camera_out(doc)


@router.put("/{camera_id}", response_model=CameraOut)
async def update_camera(camera_id: str, data: CameraUpdate, user: dict = Depends(get_current_user)):
    doc = await camera_service.update_camera(user["_id"], camera_id, data)
    return camera_service.to_camera_out(doc)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(camera_id: str, user: dict = Depends(get_current_user)):
    await camera_service.delete_camera(user["_id"], camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- processing control


@router.post("/{camera_id}/start", response_model=CameraLiveStatus, status_code=status.HTTP_202_ACCEPTED)
async def start_camera(camera_id: str, user: dict = Depends(get_current_user)):
    """Start detection/tracking for this camera in a background worker."""
    worker = await camera_service.start_camera(user["_id"], camera_id)
    return CameraLiveStatus(**worker.status())


@router.post("/{camera_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_camera(camera_id: str, user: dict = Depends(get_current_user)):
    await camera_service.stop_camera(user["_id"], camera_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{camera_id}/live", response_model=CameraLiveStatus)
async def live_status(camera_id: str, user: dict = Depends(get_current_user)):
    """Current runtime stats of a running camera (people in view, counts, fps)."""
    camera = await camera_service.get_camera(user["_id"], camera_id)
    worker = manager.get(str(camera["_id"]))
    if worker is None:
        raise ConflictError("Camera is not running")
    return CameraLiveStatus(**worker.status())


@router.get("/{camera_id}/snapshot", responses={200: {"content": {"image/jpeg": {}}}})
async def snapshot(camera_id: str, user: dict = Depends(get_current_user_from_query)):
    """A single JPEG frame (used to place the entry line). Accepts ?token= like /stream."""
    jpeg = await camera_service.get_snapshot(user["_id"], camera_id)
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


STREAM_BOUNDARY = "frame"


@router.get("/{camera_id}/stream")
async def stream(camera_id: str, request: Request, user: dict = Depends(get_current_user_from_query)):
    """MJPEG stream of annotated frames. Use directly as <img src=".../stream?token=JWT">."""
    camera = await camera_service.get_camera(user["_id"], camera_id)
    cid = str(camera["_id"])
    if not manager.is_running(cid):
        raise ConflictError("Camera is not running")

    async def frames():
        last_seq = -1
        while not await request.is_disconnected():
            worker = manager.get(cid)
            if worker is None or not worker.is_alive():
                break
            seq, jpeg = worker.latest_jpeg()
            if jpeg and seq != last_seq:
                last_seq = seq
                yield (
                    f"--{STREAM_BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                    f"Content-Length: {len(jpeg)}\r\n\r\n"
                ).encode() + jpeg + b"\r\n"
            await asyncio.sleep(0.03)

    return StreamingResponse(
        frames(),
        media_type=f"multipart/x-mixed-replace; boundary={STREAM_BOUNDARY}",
        headers={"Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no"},
    )
