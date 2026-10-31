"""Seed SYNTHETIC history so the dashboard charts have something to show.

Live processing only produces data while a camera runs. For a demo, this script
creates a camera named "Demo Lobby (synthetic)" for a user and fills it with
N days of generated visits: sessions, entry/exit events and occupancy samples.
Every generated document has `demo: True`, and --clear removes all of it.

Usage:
    python -m scripts.seed_demo --email demo@example.com            # 14 days
    python -m scripts.seed_demo --email demo@example.com --days 30
    python -m scripts.seed_demo --email demo@example.com --clear
"""
import argparse
import math
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from pymongo import MongoClient

from app.core.config import settings
from app.core.security import hash_password
from app.database.indexes import CAMERAS, EVENTS, OCCUPANCY, TRACKING_SESSIONS, USERS

DEMO_CAMERA = "Demo Lobby (synthetic)"
SNAPSHOT_MINUTES = 5


def hourly_rate(hour: int, weekday: int) -> float:
    """Expected arrivals per hour: open 08-21, lunch and evening peaks, quieter weekends."""
    if hour < 8 or hour >= 21:
        return 0.3
    lunch = 14 * math.exp(-((hour - 12.5) ** 2) / 2)
    evening = 18 * math.exp(-((hour - 17.5) ** 2) / 2.5)
    base = 4 + lunch + evening
    return base * (0.6 if weekday >= 5 else 1.0)


def poisson(lam: float, rng: random.Random) -> int:
    # Knuth's algorithm: fine for small lambda
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--tz", default="Asia/Kolkata", help="timezone used for opening hours")
    ap.add_argument("--clear", action="store_true", help="remove demo data and exit")
    ap.add_argument("--create-user", action="store_true", help="create the user (password demo12345) if missing")
    args = ap.parse_args()

    db = MongoClient(settings.MONGODB_URI, tz_aware=True)[settings.MONGODB_DB]
    user = db[USERS].find_one({"email": args.email.lower()})
    if user is None:
        if not args.create_user:
            raise SystemExit(f"No user {args.email}. Register first or pass --create-user.")
        uid = db[USERS].insert_one({"email": args.email.lower(), "full_name": "Demo User",
                                    "password_hash": hash_password("demo12345"),
                                    "created_at": datetime.now(timezone.utc)}).inserted_id
        user = db[USERS].find_one({"_id": uid})
        print(f"created user {args.email} / demo12345")

    owner = user["_id"]
    existing = db[CAMERAS].find_one({"owner_id": owner, "name": DEMO_CAMERA})
    if existing:
        for coll in (TRACKING_SESSIONS, EVENTS, OCCUPANCY):
            db[coll].delete_many({"camera_id": existing["_id"], "demo": True})
        db[CAMERAS].delete_one({"_id": existing["_id"]})
        print("removed previous demo data")
    if args.clear:
        return

    now = datetime.now(timezone.utc)
    cam_id = db[CAMERAS].insert_one({
        "owner_id": owner, "name": DEMO_CAMERA, "location": "Synthetic data for charts",
        "source_type": "file", "source": "people-detection.mp4", "is_active": False,
        "line": {"x1": 0.0, "y1": 0.6, "x2": 1.0, "y2": 0.6}, "entry_direction": "up",
        "status": "idle", "last_error": None, "created_at": now, "updated_at": now, "demo": True,
    }).inserted_id

    tz = ZoneInfo(args.tz)
    rng = random.Random(42)
    sessions, events = [], []
    local_today = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    seq = 0
    for d in range(args.days - 1, -1, -1):
        day = local_today - timedelta(days=d)
        for hour in range(24):
            for _ in range(poisson(hourly_rate(hour, day.weekday()), rng)):
                first_seen = (day + timedelta(hours=hour, seconds=rng.uniform(0, 3600))).astimezone(timezone.utc)
                duration = min(rng.lognormvariate(math.log(12 * 60), 0.7), 3 * 3600)
                last_seen = first_seen + timedelta(seconds=duration)
                if last_seen > now:
                    continue
                seq += 1
                pid = f"P-D{seq:05d}"
                entry, exit_ = first_seen + timedelta(seconds=3), last_seen - timedelta(seconds=3)
                sessions.append({
                    "camera_id": cam_id, "owner_id": owner, "person_id": pid, "track_id": seq,
                    "status": "closed", "first_seen": first_seen, "last_seen": last_seen,
                    "duration_seconds": round(duration, 1), "entry_time": entry, "exit_time": exit_,
                    "demo": True,
                })
                for kind, ts in (("entry", entry), ("exit", exit_)):
                    events.append({"camera_id": cam_id, "owner_id": owner, "person_id": pid, "track_id": seq,
                                   "type": kind, "timestamp": ts, "demo": True})

    if sessions:
        ids = db[TRACKING_SESSIONS].insert_many(sessions).inserted_ids
        by_pid = {s["person_id"]: i for s, i in zip(sessions, ids)}
        for e in events:
            e["session_id"] = by_pid[e["person_id"]]
        db[EVENTS].insert_many(events)

    # Occupancy samples: how many generated visits overlap each sample time
    start = (local_today - timedelta(days=args.days - 1)).astimezone(timezone.utc)
    intervals = sorted((s["first_seen"], s["last_seen"]) for s in sessions)
    snaps, t = [], start
    entries = exits = 0
    while t <= now:
        in_view = sum(1 for a, b in intervals if a <= t < b)
        entries = sum(1 for a, _ in intervals if a <= t)
        exits = sum(1 for _, b in intervals if b <= t)
        snaps.append({"camera_id": cam_id, "owner_id": owner, "timestamp": t, "in_view": in_view,
                      "inside": in_view, "entries": entries, "exits": exits, "demo": True})
        t += timedelta(minutes=SNAPSHOT_MINUTES)
    if snaps:
        db[OCCUPANCY].insert_many(snaps)

    print(f"seeded {len(sessions)} sessions, {len(events)} events, {len(snaps)} occupancy samples "
          f"over {args.days} days on camera '{DEMO_CAMERA}'")


if __name__ == "__main__":
    main()
