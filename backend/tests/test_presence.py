from datetime import datetime, timedelta, timezone
from itertools import count

from app.cv.detector import TrackedPerson
from app.cv.line_counter import Line, LineCounter
from app.cv.presence import LineCrossed, PresenceTracker, SessionEnded, SessionStarted

T0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


def person(tid, cy):
    """A 20x40 box whose bottom edge (feet) is at y=cy."""
    return TrackedPerson(tid, 40, cy - 40, 60, cy, 0.9)


def make_tracker(min_hits=3, lost_seconds=2.0):
    seq = count(1)
    return PresenceTracker(
        LineCounter(Line(0, 50, 100, 50), "down"),
        next_person_id=lambda: f"P-{next(seq):04d}",
        min_hits=min_hits,
        lost_seconds=lost_seconds,
    )


def run(tracker, frames, start=T0, step=0.1):
    events = []
    for i, people in enumerate(frames):
        events += tracker.update(start + timedelta(seconds=i * step), people)
    return events


def test_session_starts_only_after_min_hits():
    t = make_tracker(min_hits=3)
    events = run(t, [[person(1, 10)], [person(1, 12)]])
    assert events == []
    events = t.update(T0 + timedelta(seconds=1), [person(1, 14)])
    assert isinstance(events[0], SessionStarted)
    assert events[0].person_id == "P-0001"
    assert events[0].first_seen == T0  # backdated to the first sighting


def test_full_visit_entry_then_session_end_with_duration():
    t = make_tracker(min_hits=2, lost_seconds=1.0)
    frames = [[person(1, y)] for y in (10, 20, 30, 40, 60, 70, 80)]
    events = run(t, frames)
    kinds = [type(e).__name__ for e in events]
    assert kinds == ["SessionStarted", "LineCrossed"]
    assert events[1].type == "entry"
    assert t.inside == 1
    assert len(t.in_view) == 1

    # Person disappears; 1.5s later the session is closed
    last_seen = T0 + timedelta(seconds=0.6)
    ended = t.update(last_seen + timedelta(seconds=1.5), [])
    assert len(ended) == 1 and isinstance(ended[0], SessionEnded)
    assert ended[0].duration_seconds == 0.6
    assert ended[0].entry_time is not None and ended[0].exit_time is None
    assert t.in_view == []


def test_crossing_before_confirmation_is_not_lost():
    t = make_tracker(min_hits=3)
    events = run(t, [[person(1, 40)], [person(1, 60)], [person(1, 70)]])
    assert [type(e) for e in events] == [SessionStarted, LineCrossed]


def test_noise_tracks_are_never_reported():
    t = make_tracker(min_hits=5, lost_seconds=0.5)
    run(t, [[person(9, 10)], [person(9, 10)]])
    assert t.update(T0 + timedelta(seconds=5), []) == []


def test_exit_decrements_inside_but_not_below_zero():
    t = make_tracker(min_hits=1)
    events = run(t, [[person(1, 80)], [person(1, 20)]])
    assert [e.type for e in events if isinstance(e, LineCrossed)] == ["exit"]
    assert t.inside == 0


def test_close_all_ends_open_sessions():
    t = make_tracker(min_hits=1)
    run(t, [[person(1, 10), person(2, 90)]])
    ended = t.close_all()
    assert sorted(e.person_id for e in ended) == ["P-0001", "P-0002"]
    assert t.tracks == {}
