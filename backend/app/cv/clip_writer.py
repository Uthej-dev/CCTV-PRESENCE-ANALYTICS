"""Encodes frames into a browser-playable H.264 MP4 by piping raw frames into ffmpeg.

ffmpeg comes from the imageio-ffmpeg wheel (a static build with libx264), so no
system install is needed locally or in Docker.

Frames arrive at an uneven rate (processing speed varies), but the video must
play back in real time so that "offset N seconds into the clip" matches the
wall clock. write() therefore repeats or drops frames to keep the clip's frame
count in step with elapsed time.
"""
import subprocess
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np


def output_size(width: int, height: int, max_width: int) -> tuple[int, int]:
    """Scale down to max_width, keeping aspect ratio; H.264 (yuv420p) needs even dimensions."""
    if width > max_width:
        height = round(height * max_width / width)
        width = max_width
    return width - width % 2, height - height % 2


class ClipWriter:
    def __init__(self, path: Path, size: tuple[int, int], fps: float, start_mono: float, crf: int = 28):
        self.path = path
        self.size = size
        self.fps = fps
        self.start_mono = start_mono
        self.frames = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        w, h = size
        self._proc = subprocess.Popen(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", f"{fps:g}", "-i", "-",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",  # index at the start so browsers can seek immediately
                str(path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def fit(self, frame: np.ndarray) -> np.ndarray:
        if (frame.shape[1], frame.shape[0]) != self.size:
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        return frame

    def write(self, frame: np.ndarray, mono: float) -> None:
        target = int((mono - self.start_mono) * self.fps) + 1  # frames that "should" exist by now
        repeats = min(target - self.frames, int(self.fps * 2))  # catch up after a stall, max 2 s
        if repeats <= 0:
            return  # ahead of real time: drop this frame
        data = self.fit(frame).tobytes()
        for _ in range(repeats):
            self._proc.stdin.write(data)
        self.frames += repeats

    @property
    def duration(self) -> float:
        return self.frames / self.fps

    def close(self, timeout: float = 60) -> bool:
        """Finish the file. Returns True if ffmpeg produced a valid video."""
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=timeout)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            self._proc.kill()
            return False
        return self._proc.returncode == 0 and self.frames > 0 and self.path.is_file()

    def abort(self) -> None:
        self._proc.kill()
        self.path.unlink(missing_ok=True)
