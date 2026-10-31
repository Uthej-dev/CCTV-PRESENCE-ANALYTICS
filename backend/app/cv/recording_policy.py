"""Decides when a video clip starts and stops (pure logic, unit-tested).

    nobody ──someone appears──▶ RECORDING ──nobody for post_roll s──▶ stop
                                    │
                                    └── clip longer than max_clip s ──▶ stop + start a new clip
"""


class RecordingPolicy:
    def __init__(self, post_roll: float = 5.0, max_clip: float = 300.0):
        self.post_roll = post_roll
        self.max_clip = max_clip
        self.recording = False
        self._started = 0.0
        self._last_people = 0.0

    def update(self, now: float, in_view: int) -> list[str]:
        """now: monotonic seconds. Returns the actions to take, in order: "stop" and/or "start"."""
        if in_view > 0:
            self._last_people = now
        if self.recording:
            if now - self._last_people >= self.post_roll:
                self.recording = False
                return ["stop"]
            if now - self._started >= self.max_clip:
                self._started = now
                return ["stop", "start"]
            return []
        if in_view > 0:
            self.recording = True
            self._started = now
            return ["start"]
        return []
