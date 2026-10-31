"""Virtual line crossing logic (pure Python, no OpenCV -> easy to unit test).

Each tracked person is reduced to one anchor point (bottom-centre of the box,
i.e. roughly their feet). For every track we remember which side of the line
the point was on. When the side flips, the person crossed the line:

    side = sign( cross(B - A, P - A) )      A, B = line endpoints, P = point

The configured entry direction (down/up/left/right) decides which side is
"inside": moving onto that side is an ENTRY, moving off it is an EXIT.

A small dead-zone around the line (hysteresis) stops jitter of the box from
producing repeated entry/exit events while someone stands on the line.
"""
from dataclasses import dataclass

DIRECTION_VECTORS = {
    "down": (0.0, 1.0),  # image y axis points down
    "up": (0.0, -1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}

ENTRY = "entry"
EXIT = "exit"


@dataclass
class Line:
    x1: float
    y1: float
    x2: float
    y2: float


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


class LineCounter:
    def __init__(self, line: Line, entry_direction: str = "down", dead_zone: float = 0.0):
        """
        line:            endpoints in pixel coordinates
        entry_direction: one of down/up/left/right
        dead_zone:       distance in pixels from the line within which a point has no side
        """
        self.line = line
        self.dead_zone = dead_zone
        self._dx = line.x2 - line.x1
        self._dy = line.y2 - line.y1
        self._length = (self._dx ** 2 + self._dy ** 2) ** 0.5 or 1.0

        ex, ey = DIRECTION_VECTORS[entry_direction]
        inside = _cross(self._dx, self._dy, ex, ey)
        # If the direction is parallel to the line, fall back to the line's normal
        self._inside_sign = 1 if inside >= 0 else -1

        self._last_side: dict[int, int] = {}
        self.entries = 0
        self.exits = 0

    def _signed_distance(self, x: float, y: float) -> float:
        return _cross(self._dx, self._dy, x - self.line.x1, y - self.line.y1) / self._length

    def _within_segment(self, x: float, y: float) -> bool:
        """Is the point's projection onto the line inside the segment (with 5% slack)?"""
        t = ((x - self.line.x1) * self._dx + (y - self.line.y1) * self._dy) / (self._length ** 2)
        return -0.05 <= t <= 1.05

    def update(self, track_id: int, x: float, y: float) -> str | None:
        """Feed a track's new anchor point. Returns 'entry', 'exit' or None."""
        dist = self._signed_distance(x, y)
        if abs(dist) <= self.dead_zone:
            return None  # inside the dead zone: keep the previous side
        side = 1 if dist > 0 else -1

        prev = self._last_side.get(track_id)
        self._last_side[track_id] = side
        if prev is None or prev == side or not self._within_segment(x, y):
            return None

        if side == self._inside_sign:
            self.entries += 1
            return ENTRY
        self.exits += 1
        return EXIT

    def is_inside(self, x: float, y: float) -> bool:
        return (1 if self._signed_distance(x, y) > 0 else -1) == self._inside_sign

    def forget(self, track_id: int) -> None:
        self._last_side.pop(track_id, None)

    def reset(self) -> None:
        self._last_side.clear()
