import subprocess

import imageio_ffmpeg
import numpy as np

from app.cv.clip_writer import ClipWriter, output_size


def probe(path):
    out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    return out


def test_output_size_is_even_and_capped():
    assert output_size(1920, 1080, 960) == (960, 540)
    assert output_size(768, 432, 960) == (768, 432)
    assert output_size(1001, 563, 2000) == (1000, 562)


def test_writes_h264_mp4_in_real_time(tmp_path):
    path = tmp_path / "clip.mp4"
    w = ClipWriter(path, (320, 180), fps=10, start_mono=100.0)
    frame = np.zeros((360, 640, 3), np.uint8)  # bigger than output: gets resized
    # 3 seconds of wall time, but frames arrive unevenly (and with a 1 s stall)
    for t in [100.0, 100.1, 100.2, 100.3, 101.3, 101.4, 102.9]:
        w.write(frame, t)
    assert w.frames == 30  # 2.9 s * 10 fps + 1
    assert w.close()
    info = probe(path)
    assert "h264" in info and "320x180" in info
    assert "Duration: 00:00:03.00" in info


def test_frames_arriving_too_fast_are_dropped(tmp_path):
    w = ClipWriter(tmp_path / "c.mp4", (64, 64), fps=10, start_mono=0.0)
    frame = np.zeros((64, 64, 3), np.uint8)
    for i in range(10):
        w.write(frame, i * 0.01)  # 10 frames within 0.1 s
    assert w.frames == 1
    w.close()
