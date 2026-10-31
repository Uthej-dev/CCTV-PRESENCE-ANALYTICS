from app.cv.line_counter import ENTRY, EXIT, Line, LineCounter

# Horizontal line across a 100x100 frame at y=50
H_LINE = Line(0, 50, 100, 50)


def walk(counter, track_id, points):
    return [e for e in (counter.update(track_id, x, y) for x, y in points) if e]


def test_moving_down_is_entry_when_direction_down():
    c = LineCounter(H_LINE, "down")
    assert walk(c, 1, [(50, 10), (50, 40), (50, 60), (50, 90)]) == [ENTRY]
    assert (c.entries, c.exits) == (1, 0)


def test_moving_up_is_exit_when_direction_down():
    c = LineCounter(H_LINE, "down")
    assert walk(c, 1, [(50, 90), (50, 60), (50, 40)]) == [EXIT]


def test_direction_up_inverts():
    c = LineCounter(H_LINE, "up")
    assert walk(c, 1, [(50, 90), (50, 10)]) == [ENTRY]


def test_line_drawn_right_to_left_gives_same_result():
    c = LineCounter(Line(100, 50, 0, 50), "down")
    assert walk(c, 1, [(50, 10), (50, 90)]) == [ENTRY]


def test_vertical_line_left_right():
    c = LineCounter(Line(50, 0, 50, 100), "right")
    assert walk(c, 1, [(10, 50), (90, 50)]) == [ENTRY]
    assert walk(c, 2, [(90, 50), (10, 50)]) == [EXIT]


def test_dead_zone_suppresses_jitter():
    c = LineCounter(H_LINE, "down", dead_zone=5)
    # Hovering around the line within +-5px must not produce events
    events = walk(c, 1, [(50, 30), (50, 48), (50, 52), (50, 49), (50, 53), (50, 70)])
    assert events == [ENTRY]


def test_crossing_outside_segment_is_ignored():
    c = LineCounter(Line(0, 50, 40, 50), "down")  # short line on the left
    assert walk(c, 1, [(80, 10), (80, 90)]) == []


def test_tracks_are_independent():
    c = LineCounter(H_LINE, "down")
    c.update(1, 50, 10)
    c.update(2, 50, 90)
    assert c.update(1, 50, 90) == ENTRY
    assert c.update(2, 50, 10) == EXIT
