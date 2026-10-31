"""Turns per-frame tracks into presence sessions and entry/exit events.

Pure logic (no OpenCV, no DB): the camera worker feeds it tracked people for
each frame and persists the events it returns.

Session lifecycle for one track ID:
    first seen ──(MIN_TRACK_HITS frames)──▶ confirmed  -> SessionStarted
    crosses line                           -> LineCrossed (entry / exit)
    unseen for TRACK_LOST_SECONDS          -> SessionEnded (duration = last_seen - first_seen)

Short-lived tracks that never reach MIN_TRACK_HITS are treated as noise
(false detections) and never stored.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from app.cv.detector import TrackedPerson
from app.cv.line_counter import ENTRY, LineCounter


@dataclass
class SessionStarted:
    track_id: int
    person_id: str
    first_seen: datetime


@dataclass
class LineCrossed:
    track_id: int
    person_id: str
    type: str  # "entry" | "exit"
    timestamp: datetime


@dataclass
class SessionEnded:
    track_id: int
    person_id: str
    first_seen: datetime
    last_seen: datetime
    entry_time: datetime | None
    exit_time: datetime | None

    @property
    def duration_seconds(self) -> float:
        return (self.last_seen - self.first_seen).total_seconds()


PresenceEvent = SessionStarted | LineCrossed | SessionEnded


@dataclass
class TrackState:
    track_id: int
    first_seen: datetime
    last_seen: datetime
    hits: int = 0
    person_id: str | None = None
    entry_time: datetime | None = None
    exit_time: datetime | None = None
    box: tuple[float, float, float, float] = (0, 0, 0, 0)
    pending: list[tuple[str, datetime]] = field(default_factory=list)  # crossings before confirmation

    @property
    def confirmed(self) -> bool:
        return self.person_id is not None


class PresenceTracker:
    def __init__(
        self,
        line: LineCounter,
        next_person_id: Callable[[], str],
        min_hits: int = 4,
        lost_seconds: float = 2.0,
    ):
        self.line = line
        self.next_person_id = next_person_id
        self.min_hits = min_hits
        self.lost_seconds = lost_seconds
        self.tracks: dict[int, TrackState] = {}
        self.inside = 0       # net occupancy from line crossings (entries - exits, never < 0)
        self.in_view: list[TrackState] = []  # confirmed people visible in the latest frame

    def update(self, now: datetime, people: list[TrackedPerson]) -> list[PresenceEvent]:
        events: list[PresenceEvent] = []
        visible: list[TrackState] = []

        for p in people:
            st = self.tracks.get(p.track_id)
            if st is None:
                st = self.tracks[p.track_id] = TrackState(p.track_id, first_seen=now, last_seen=now)
            st.hits += 1
            st.last_seen = now
            st.box = (p.x1, p.y1, p.x2, p.y2)

            crossing = self.line.update(p.track_id, *p.anchor)
            if crossing:
                st.pending.append((crossing, now))

            if not st.confirmed and st.hits >= self.min_hits:
                st.person_id = self.next_person_id()
                events.append(SessionStarted(st.track_id, st.person_id, st.first_seen))

            if st.confirmed:
                for kind, ts in st.pending:
                    events.append(self._record_crossing(st, kind, ts))
                st.pending.clear()
                visible.append(st)

        events.extend(self._expire(now))
        self.in_view = visible
        return events

    def _record_crossing(self, st: TrackState, kind: str, ts: datetime) -> LineCrossed:
        if kind == ENTRY:
            st.entry_time = ts
            self.inside += 1
        else:
            st.exit_time = ts
            self.inside = max(0, self.inside - 1)
        return LineCrossed(st.track_id, st.person_id, kind, ts)

    def _end(self, st: TrackState) -> SessionEnded:
        return SessionEnded(st.track_id, st.person_id, st.first_seen, st.last_seen, st.entry_time, st.exit_time)

    def _expire(self, now: datetime) -> list[SessionEnded]:
        ended = []
        for tid, st in list(self.tracks.items()):
            if (now - st.last_seen).total_seconds() > self.lost_seconds:
                del self.tracks[tid]
                self.line.forget(tid)
                if st.confirmed:
                    ended.append(self._end(st))
        return ended

    def close_all(self) -> list[SessionEnded]:
        """End every open session (camera stopped / video looped)."""
        ended = [self._end(st) for st in self.tracks.values() if st.confirmed]
        self.tracks.clear()
        self.line.reset()
        self.in_view = []
        return ended

    def active_sessions(self) -> list[TrackState]:
        return [st for st in self.tracks.values() if st.confirmed]
