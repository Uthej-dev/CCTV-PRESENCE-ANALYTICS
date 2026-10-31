"""Seeds known sessions/events/snapshots and checks the aggregation results."""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo import MongoClient

from app.core.config import settings

IST = timezone(timedelta(hours=5, minutes=30))  # Asia/Kolkata, no DST
DAY = "2026-03-10"


def ist(h, m=0, s=0, day=10):
    return datetime(2026, 3, day, h, m, s, tzinfo=IST).astimezone(timezone.utc)


def seed(client, auth_headers):
    owner = ObjectId(client.get("/auth/me", headers=auth_headers).json()["id"])
    cam = ObjectId(client.post("/cameras", json={"name": "Door", "source": "x.mp4"}, headers=auth_headers).json()["id"])
    db = MongoClient(settings.MONGODB_URI)[settings.MONGODB_DB]
    base = {"owner_id": owner, "camera_id": cam}

    def session(first_seen, duration):
        db.tracking_sessions.insert_one({**base, "person_id": "P", "track_id": 1, "status": "closed",
                                         "first_seen": first_seen, "last_seen": first_seen + timedelta(seconds=duration),
                                         "duration_seconds": duration, "entry_time": None, "exit_time": None})

    # March 10 (IST): 3 visitors at 09:xx, 1 at 14:xx, plus a 0.3s noise track that must be ignored
    session(ist(9, 5), 60)
    session(ist(9, 30), 120)
    session(ist(9, 45), 180)
    session(ist(14, 0), 240)
    session(ist(15, 0), 0.3)
    # 00:30 IST on March 10 is still March 9 in UTC -> must count for March 10 in IST
    session(ist(0, 30), 60)
    # March 9 (IST): 1 visitor
    session(ist(12, 0, day=9), 30)

    for ts, kind in [(ist(9, 6), "entry"), (ist(9, 31), "entry"), (ist(9, 50), "exit"), (ist(14, 1), "entry")]:
        db.events.insert_one({**base, "person_id": "P", "track_id": 1, "type": kind, "timestamp": ts})

    for ts, n in [(ist(9, 0), 1), (ist(9, 40), 3), (ist(9, 40, 30), 2), (ist(14, 0), 1)]:
        db.occupancy_snapshots.insert_one({**base, "timestamp": ts, "in_view": n, "inside": n, "entries": 0, "exits": 0})
    return cam


def test_daily(client, auth_headers):
    seed(client, auth_headers)
    d = client.get(f"/analytics/daily?date={DAY}&tz=Asia/Kolkata", headers=auth_headers).json()
    assert d["visitors"] == 5                       # noise track excluded, 00:30 IST included
    assert d["entries"] == 3 and d["exits"] == 1
    assert d["avg_duration_seconds"] == 132.0       # (60+120+180+240+60)/5
    assert d["max_duration_seconds"] == 240
    assert d["peak_occupancy"] == 3
    assert d["peak_hour"] == 9
    assert d["hourly"][9] == {"hour": 9, "visitors": 3, "entries": 2, "exits": 1}
    assert d["hourly"][0]["visitors"] == 1


def test_daily_in_utc_shifts_buckets(client, auth_headers):
    seed(client, auth_headers)
    d = client.get(f"/analytics/daily?date={DAY}&tz=UTC", headers=auth_headers).json()
    # In UTC the 00:30 IST visit falls on March 9
    assert d["visitors"] == 4
    assert d["peak_hour"] == 4  # 09:30 and 09:45 IST fall in the 04:00 UTC hour


def test_weekly(client, auth_headers):
    seed(client, auth_headers)
    w = client.get(f"/analytics/weekly?end_date={DAY}&days=7&tz=Asia/Kolkata", headers=auth_headers).json()
    assert len(w["days"]) == 7
    assert w["days"][-1]["date"] == DAY and w["days"][-1]["visitors"] == 5
    assert w["days"][-2]["visitors"] == 1
    assert w["total_visitors"] == 6
    assert w["busiest_day"] == DAY
    assert w["peak_hour"] == 9
    assert w["days"][-1]["peak_occupancy"] == 3


def test_occupancy_series(client, auth_headers):
    seed(client, auth_headers)
    start = ist(9).isoformat()
    end = ist(15).isoformat()
    o = client.get("/analytics/occupancy", params={"start": start, "end": end, "interval_minutes": 60,
                                                    "tz": "Asia/Kolkata"}, headers=auth_headers).json()
    assert [p["occupancy"] for p in o["points"]] == [3, 1]
    assert o["peak_occupancy"] == 3


def test_camera_filter_and_validation(client, auth_headers):
    seed(client, auth_headers)
    other = client.post("/cameras", json={"name": "Other", "source": "y.mp4"}, headers=auth_headers).json()["id"]
    d = client.get(f"/analytics/daily?date={DAY}&tz=Asia/Kolkata&camera_id={other}", headers=auth_headers).json()
    assert d["visitors"] == 0 and d["peak_hour"] is None
    assert client.get("/analytics/daily?tz=Mars/Base", headers=auth_headers).status_code == 422
    assert client.get("/analytics/weekly?days=99", headers=auth_headers).status_code == 422
