from fastapi import APIRouter

from app.api import analytics, auth, cameras, detections, recordings, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cameras.router)
api_router.include_router(detections.router)
api_router.include_router(analytics.router)
api_router.include_router(system.router)
api_router.include_router(recordings.router)
