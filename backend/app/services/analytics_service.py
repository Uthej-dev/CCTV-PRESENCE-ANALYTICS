"""Analytics computed on demand with MongoDB aggregation pipelines.

Definitions
-----------
visitor          a tracking session lasting >= MIN_VISIT_SECONDS (shorter ones are tracker noise)
presence time    session duration (first_seen -> last_seen)
entries / exits  line-crossing events
occupancy        people in view at the same time, from occupancy_snapshots
                 (per camera: max within a time bucket; across cameras: summed)
peak hour        hour of day with the most visitors

All day/hour boundaries are computed in the caller's timezone (IANA name, e.g.
"Asia/Kolkata"), so "today" means the user's today, not UTC's.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.database.indexes import EVENTS, OCCUPANCY, TRACKING_SESSIONS
from app.database.mongodb import get_db


def resolve_tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or settings.TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValidationError(f"Unknown timezone: {name}")


def today_in(tz: ZoneInfo) -> date:
    return datetime.now(tz).date()


def day_bounds(day: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC [start, end) of a calendar day in `tz` (DST-safe)."""
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _base(owner_id: ObjectId, camera_id: ObjectId | None) -> dict:
    q: dict = {"owner_id": owner_id}
    if camera_id is not None:
        q["camera_id"] = camera_id
    return q


def _visit_match(owner_id, camera_id, start, end) -> dict:
    return {
        **_base(owner_id, camera_id),
        "first_seen": {"$gte": start, "$lt": end},
        "duration_seconds": {"$gte": settings.MIN_VISIT_SECONDS},
    }


def _occupancy_buckets(owner_id, camera_id, start, end, interval: int, tz: str) -> list[dict]:
    """Pipeline stages producing {_id: bucket_start, occupancy, inside} sorted by time."""
    return [
        {"$match": {**_base(owner_id, camera_id), "timestamp": {"$gte": start, "$lt": end}}},
        {"$group": {
            "_id": {
                "camera": "$camera_id",
                "bucket": {"$dateTrunc": {"date": "$timestamp", "unit": "minute", "binSize": interval, "timezone": tz}},
            },
            "occupancy": {"$max": "$in_view"},
            "inside": {"$max": "$inside"},
        }},
        {"$group": {"_id": "$_id.bucket", "occupancy": {"$sum": "$occupancy"}, "inside": {"$sum": "$inside"}}},
        {"$sort": {"_id": 1}},
    ]


# ---------------------------------------------------------------- daily

async def daily(owner_id: ObjectId, day: date | None, tz_name: str | None, camera_id: ObjectId | None) -> dict:
    tz = resolve_tz(tz_name)
    day = day or today_in(tz)
    start, end = day_bounds(day, tz)
    db = get_db()

    sessions = await (await db[TRACKING_SESSIONS].aggregate([
        {"$match": _visit_match(owner_id, camera_id, start, end)},
        {"$facet": {
            "totals": [{"$group": {
                "_id": None,
                "visitors": {"$sum": 1},
                "avg": {"$avg": "$duration_seconds"},
                "max": {"$max": "$duration_seconds"},
            }}],
            "hourly": [{"$group": {
                "_id": {"$hour": {"date": "$first_seen", "timezone": tz.key}},
                "visitors": {"$sum": 1},
            }}],
        }},
    ])).to_list()
    facet = sessions[0]
    totals = facet["totals"][0] if facet["totals"] else {"visitors": 0, "avg": 0, "max": 0}

    events = await (await db[EVENTS].aggregate([
        {"$match": {**_base(owner_id, camera_id), "timestamp": {"$gte": start, "$lt": end}}},
        {"$group": {
            "_id": {"hour": {"$hour": {"date": "$timestamp", "timezone": tz.key}}, "type": "$type"},
            "count": {"$sum": 1},
        }},
    ])).to_list()

    peak = await (await db[OCCUPANCY].aggregate([
        *_occupancy_buckets(owner_id, camera_id, start, end, 1, tz.key),
        {"$sort": {"occupancy": -1, "_id": 1}},
        {"$limit": 1},
    ])).to_list()

    hourly = {h: {"hour": h, "visitors": 0, "entries": 0, "exits": 0} for h in range(24)}
    for row in facet["hourly"]:
        hourly[row["_id"]]["visitors"] = row["visitors"]
    for row in events:
        hourly[row["_id"]["hour"]]["entries" if row["_id"]["type"] == "entry" else "exits"] += row["count"]

    peak_hour = max(hourly.values(), key=lambda b: b["visitors"]) if totals["visitors"] else None
    return {
        "date": day,
        "timezone": tz.key,
        "visitors": totals["visitors"],
        "entries": sum(b["entries"] for b in hourly.values()),
        "exits": sum(b["exits"] for b in hourly.values()),
        "avg_duration_seconds": round(totals["avg"] or 0, 1),
        "max_duration_seconds": round(totals["max"] or 0, 1),
        "peak_occupancy": peak[0]["occupancy"] if peak else 0,
        "peak_occupancy_time": peak[0]["_id"] if peak else None,
        "peak_hour": peak_hour["hour"] if peak_hour else None,
        "hourly": list(hourly.values()),
    }


# ---------------------------------------------------------------- weekly / multi-day

async def weekly(
    owner_id: ObjectId, end_date: date | None, days: int, tz_name: str | None, camera_id: ObjectId | None
) -> dict:
    tz = resolve_tz(tz_name)
    end_date = end_date or today_in(tz)
    start_date = end_date - timedelta(days=days - 1)
    start, _ = day_bounds(start_date, tz)
    _, end = day_bounds(end_date, tz)
    db = get_db()
    day_expr = lambda field: {"$dateToString": {"format": "%Y-%m-%d", "date": field, "timezone": tz.key}}  # noqa: E731

    sessions = await (await db[TRACKING_SESSIONS].aggregate([
        {"$match": _visit_match(owner_id, camera_id, start, end)},
        {"$facet": {
            "by_day": [{"$group": {
                "_id": day_expr("$first_seen"),
                "visitors": {"$sum": 1},
                "total_duration": {"$sum": "$duration_seconds"},
            }}],
            "by_hour": [{"$group": {
                "_id": {"$hour": {"date": "$first_seen", "timezone": tz.key}},
                "visitors": {"$sum": 1},
            }}],
        }},
    ])).to_list()

    events = await (await db[EVENTS].aggregate([
        {"$match": {**_base(owner_id, camera_id), "timestamp": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": {"day": day_expr("$timestamp"), "type": "$type"}, "count": {"$sum": 1}}},
    ])).to_list()

    peaks = await (await db[OCCUPANCY].aggregate([
        *_occupancy_buckets(owner_id, camera_id, start, end, 1, tz.key),
        {"$group": {"_id": day_expr("$_id"), "peak": {"$max": "$occupancy"}}},
    ])).to_list()

    by_day: dict[str, dict] = {}
    for i in range(days):
        d = start_date + timedelta(days=i)
        by_day[d.isoformat()] = {"date": d, "visitors": 0, "entries": 0, "exits": 0,
                                 "avg_duration_seconds": 0.0, "peak_occupancy": 0, "_total": 0.0}
    for row in sessions[0]["by_day"]:
        if row["_id"] in by_day:
            by_day[row["_id"]].update(visitors=row["visitors"], _total=row["total_duration"])
    for row in events:
        if row["_id"]["day"] in by_day:
            by_day[row["_id"]["day"]]["entries" if row["_id"]["type"] == "entry" else "exits"] += row["count"]
    for row in peaks:
        if row["_id"] in by_day:
            by_day[row["_id"]]["peak_occupancy"] = row["peak"]

    total_visitors = sum(d["visitors"] for d in by_day.values())
    total_duration = sum(d["_total"] for d in by_day.values())
    for d in by_day.values():
        d["avg_duration_seconds"] = round(d["_total"] / d["visitors"], 1) if d["visitors"] else 0.0
        del d["_total"]

    by_hour = [0] * 24
    for row in sessions[0]["by_hour"]:
        by_hour[row["_id"]] = row["visitors"]

    day_list = list(by_day.values())
    busiest = max(day_list, key=lambda d: d["visitors"]) if total_visitors else None
    return {
        "start_date": start_date,
        "end_date": end_date,
        "timezone": tz.key,
        "total_visitors": total_visitors,
        "total_entries": sum(d["entries"] for d in day_list),
        "total_exits": sum(d["exits"] for d in day_list),
        "avg_duration_seconds": round(total_duration / total_visitors, 1) if total_visitors else 0.0,
        "busiest_day": busiest["date"] if busiest else None,
        "peak_hour": by_hour.index(max(by_hour)) if total_visitors else None,
        "days": day_list,
        "visitors_by_hour": by_hour,
    }


# ---------------------------------------------------------------- occupancy time series

async def occupancy(
    owner_id: ObjectId,
    start: datetime | None,
    end: datetime | None,
    interval_minutes: int,
    tz_name: str | None,
    camera_id: ObjectId | None,
) -> dict:
    tz = resolve_tz(tz_name)
    if start is None and end is None:
        start, end = day_bounds(today_in(tz), tz)
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(hours=24)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if start >= end:
        raise ValidationError("start must be before end")
    if (end - start) / timedelta(minutes=interval_minutes) > 5000:
        raise ValidationError("Too many points: use a larger interval or a shorter range")

    rows = await (await get_db()[OCCUPANCY].aggregate(
        _occupancy_buckets(owner_id, camera_id, start, end, interval_minutes, tz.key)
    )).to_list()
    points = [{"timestamp": r["_id"], "occupancy": r["occupancy"], "inside": r["inside"]} for r in rows]
    return {
        "start": start,
        "end": end,
        "interval_minutes": interval_minutes,
        "timezone": tz.key,
        "peak_occupancy": max((p["occupancy"] for p in points), default=0),
        "points": points,
    }
