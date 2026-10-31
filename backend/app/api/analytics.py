from datetime import date, datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.api.detections import optional_camera_oid
from app.schemas.analytics import DailyAnalytics, OccupancySeries, WeeklyAnalytics
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

TZ_DESC = "IANA timezone, e.g. Asia/Kolkata (default: server TIMEZONE)"


@router.get("/daily", response_model=DailyAnalytics)
async def daily(
    date: date | None = Query(None, description="Day to report (default: today)"),
    tz: str | None = Query(None, description=TZ_DESC),
    camera_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Visitors, entries/exits, average presence, peak occupancy and hourly breakdown for one day."""
    return await analytics_service.daily(user["_id"], date, tz, optional_camera_oid(camera_id))


@router.get("/weekly", response_model=WeeklyAnalytics)
async def weekly(
    end_date: date | None = Query(None, description="Last day of the period (default: today)"),
    days: int = Query(7, ge=1, le=31),
    tz: str | None = Query(None, description=TZ_DESC),
    camera_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Per-day visitors / durations / peaks over the last `days` days, plus visitors by hour."""
    return await analytics_service.weekly(user["_id"], end_date, days, tz, optional_camera_oid(camera_id))


@router.get("/occupancy", response_model=OccupancySeries)
async def occupancy(
    start: datetime | None = Query(None, description="ISO 8601 (default: start of today)"),
    end: datetime | None = Query(None, description="ISO 8601 (default: now)"),
    interval_minutes: int = Query(5, ge=1, le=1440),
    tz: str | None = Query(None, description=TZ_DESC),
    camera_id: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Occupancy over time, bucketed by `interval_minutes`."""
    return await analytics_service.occupancy(
        user["_id"], start, end, interval_minutes, tz, optional_camera_oid(camera_id)
    )
