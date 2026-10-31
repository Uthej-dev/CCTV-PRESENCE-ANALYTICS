"""Draws boxes, IDs, the entry line and counters onto frames for the live stream."""
import cv2
import numpy as np

from app.cv.presence import TrackState

GREEN = (80, 200, 60)
GREY = (160, 160, 160)
LINE_COLOR = (0, 200, 255)
WHITE = (255, 255, 255)
DARK = (30, 30, 30)


def _label(img, text, x, y, color):
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    y = max(y, h + 6)
    cv2.rectangle(img, (x, y - h - 6), (x + w + 6, y), color, -1)
    cv2.putText(img, text, (x + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, DARK, 1, cv2.LINE_AA)


def annotate(
    frame: np.ndarray,
    line_px: tuple[int, int, int, int],
    entry_direction: str,
    tracks: list[TrackState],
    in_view: int,
    inside: int,
    entries: int,
    exits: int,
    visible_ids: set[int],
) -> np.ndarray:
    img = frame.copy()

    # Entry/exit line + arrow showing the entry direction
    x1, y1, x2, y2 = line_px
    cv2.line(img, (x1, y1), (x2, y2), LINE_COLOR, 2, cv2.LINE_AA)
    mx, my = (x1 + x2) // 2, (y1 + y2) // 2
    dx, dy = {"down": (0, 30), "up": (0, -30), "left": (-30, 0), "right": (30, 0)}[entry_direction]
    cv2.arrowedLine(img, (mx, my), (mx + dx, my + dy), LINE_COLOR, 2, cv2.LINE_AA, tipLength=0.4)
    _label(img, "ENTRY", mx + dx + 6, my + dy + 6, LINE_COLOR)

    # People
    for st in tracks:
        if st.track_id not in visible_ids:
            continue
        bx1, by1, bx2, by2 = (int(v) for v in st.box)
        color = GREEN if st.confirmed else GREY
        cv2.rectangle(img, (bx1, by1), (bx2, by2), color, 2)
        _label(img, st.person_id or f"#{st.track_id}", bx1, by1, color)
        cv2.circle(img, ((bx1 + bx2) // 2, by2), 3, color, -1)

    # Stats panel
    panel = f"In view: {in_view}   Inside: {inside}   In: {entries}   Out: {exits}"
    (w, h), _ = cv2.getTextSize(panel, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(img, (8, 8), (8 + w + 16, 8 + h + 16), DARK, -1)
    cv2.putText(img, panel, (16, 8 + h + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
    return img


def encode_jpeg(img: np.ndarray, quality: int) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else b""
