# ---- CCTV analytics API (FastAPI + YOLO, CPU inference) ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    VIDEO_DIR=/app/data/videos \
    MEDIA_DIR=/app/data/media \
    DOWNLOAD_SAMPLES=true

# OpenCV runtime libraries + curl for the health check
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch first: the default wheel bundles CUDA and is several GB larger
COPY requirements.txt .
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Bake the YOLO weights into the image. /app/data (videos + recordings) should be a
# persistent volume; sample videos are fetched into it on first start.
RUN mkdir -p weights /app/data \
    && python -c "from ultralytics import YOLO; YOLO('weights/yolo11n.pt')"

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD curl -fs http://localhost:${PORT:-8000}/health || exit 1

# ONE uvicorn process on purpose: camera workers live in this process's memory.
# Scale out by running more instances with their own cameras, not with --workers.
CMD ["sh", "-c", "if [ \"$DOWNLOAD_SAMPLES\" = true ]; then python -m scripts.download_samples || true; fi; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
