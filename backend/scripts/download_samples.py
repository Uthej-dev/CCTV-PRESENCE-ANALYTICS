"""Download free sample videos (Intel IoT DevKit, CC-BY 4.0) into VIDEO_DIR.

Usage:  python -m scripts.download_samples
Source: https://github.com/intel-iot-devkit/sample-videos
"""
import urllib.request
from pathlib import Path

from app.core.config import settings

BASE = "https://github.com/intel-iot-devkit/sample-videos/raw/master/"
FILES = ["people-detection.mp4", "one-by-one-person-detection.mp4"]


def main() -> None:
    target = Path(settings.VIDEO_DIR)
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = target / name
        if dest.exists():
            print(f"exists     {dest}")
            continue
        print(f"download   {name}")
        urllib.request.urlretrieve(BASE + name, dest)
    print("done")


if __name__ == "__main__":
    main()
