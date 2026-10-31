from app.cv.recording_policy import RecordingPolicy


def run(policy, timeline):
    """timeline: list of (time, in_view) -> list of (time, actions) where actions happened."""
    return [(t, a) for t, n in timeline if (a := policy.update(t, n))]


def test_starts_when_someone_appears_and_stops_after_post_roll():
    p = RecordingPolicy(post_roll=5, max_clip=300)
    timeline = [(0, 0), (1, 0), (2, 1), (3, 2), (4, 1), (5, 0), (8, 0), (9.9, 0), (10, 0), (11, 0)]
    assert run(p, timeline) == [(2, ["start"]), (9.9, ["stop"])]  # last person seen at t=4, +5 s


def test_short_gap_keeps_one_clip():
    p = RecordingPolicy(post_roll=5)
    timeline = [(0, 1), (2, 0), (4, 0), (5, 1), (8, 0), (13, 0)]
    assert run(p, timeline) == [(0, ["start"]), (13, ["stop"])]


def test_long_activity_is_split():
    p = RecordingPolicy(post_roll=5, max_clip=10)
    timeline = [(t, 1) for t in range(0, 25)]
    assert run(p, timeline) == [(0, ["start"]), (10, ["stop", "start"]), (20, ["stop", "start"])]


def test_nobody_never_records():
    p = RecordingPolicy()
    assert run(p, [(t, 0) for t in range(100)]) == []
