# CCTV Human Detection & Presence Analytics

A full-stack app that processes CCTV/video footage. It detects people with **YOLO11**, tracks them across
frames with **ByteTrack**, counts **entries and exits** across a virtual line, measures **presence
duration**, stores everything in **MongoDB**, and shows live video and analytics in a **React** dashboard.

People stay anonymous: there's no face recognition, only per-visit IDs like `P-0042`.

```text
React (Vite) ──REST + JWT──▶ FastAPI ──▶ services ──▶ MongoDB
     ▲                          │
     └──── MJPEG stream ◀────── camera workers (1 thread / camera)
                                OpenCV → YOLO11n → ByteTrack → line crossing → sessions
```

## Features

- **Auth**: register, log in, bcrypt password hashing, JWT-protected API, per-user data isolation
- **Cameras**: create, edit, delete, activate and start/stop. Sources can be a video file, webcam or RTSP (with reconnect)
- **Detection & tracking**: YOLO11n (people only) and ByteTrack IDs. Noise tracks are filtered out
- **Entry/exit line**: draw it on a camera frame and choose the entry direction. A dead zone suppresses jitter
- **Presence**: one session per person visit (first seen → last seen, entry/exit times)
- **Live monitoring**: annotated MJPEG stream with boxes, IDs, line and counters, plus a live people list
- **Analytics**: current occupancy, daily visitors, entries/exits, average and longest presence, peak
  occupancy and peak hour, weekly trends, occupancy time series. Computed with timezone-aware
  MongoDB aggregation pipelines
- **Video recordings**: event-based, like an NVR. A clip starts when someone appears (with 2 s of pre-roll) and stops
  5 s after the last person leaves. Clips are annotated H.264 MP4s (via ffmpeg) with a timeline of entries, exits and
  head-count changes you can click to jump to. Filter by day, time, "2+ people at once" or person. Clips are deleted after 7 days
- **History**: paginated, filterable visits and line crossings. Each row has "▶ Video", which opens the recording at that exact moment
- **Video library**: upload clips that play in a loop like a live camera

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 19, Vite, React Router, Recharts, Axios |
| Backend | Python 3.12, FastAPI, Pydantic v2, Uvicorn |
| Computer vision | Ultralytics YOLO11n, ByteTrack, OpenCV, PyTorch (CPU / CUDA / Apple MPS), ffmpeg/H.264 (imageio-ffmpeg) |
| Database | MongoDB (PyMongo async + sync clients), Atlas in production |
| Tooling | pytest (57 tests), Vitest, ESLint, Docker, docker-compose, GitHub Actions |

## Run locally

Prerequisites: Python 3.12, Node 20+, and MongoDB (local or Atlas).

```bash
# 0. MongoDB (macOS / Homebrew)
brew services start mongodb-community

# 1. Backend: http://localhost:8000 (interactive docs at /docs)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                       # then set JWT_SECRET
python -m scripts.download_samples         # two free sample videos (Intel, CC-BY 4.0)
uvicorn app.main:app --reload --port 8000

# 2. Frontend: http://localhost:5173
cd frontend
npm install
cp .env.example .env
npm run dev
```

Register in the UI, then go to **Cameras → Add camera → Video file → people-detection.mp4 → Start detection**.

Optional demo history (synthetic data, clearly labeled, so the charts aren't empty):

```bash
cd backend && python -m scripts.seed_demo --email you@example.com          # --clear removes it
```

### With Docker

```bash
docker compose up --build        # frontend :3000, API :8000, MongoDB
```

## Tests

```bash
cd backend && pytest -q          # API, auth, cameras, line crossing, presence, analytics, detector
cd frontend && npm test && npm run lint
```

## API overview

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` · `POST /auth/logout` |
| Cameras | `GET/POST /cameras` · `GET/PUT/DELETE /cameras/{id}` |
| Processing | `POST /cameras/{id}/start` · `POST /cameras/{id}/stop` · `GET /cameras/{id}/live` · `GET /cameras/{id}/stream` (MJPEG) · `GET /cameras/{id}/snapshot` |
| Presence | `GET /presence/current` · `GET /detections` · `GET /tracking` · `GET /events` |
| Analytics | `GET /analytics/daily` · `GET /analytics/weekly` · `GET /analytics/occupancy` |
| Recordings | `GET /recordings` · `GET /recordings/at?at=` · `GET /recordings/{id}/video` (Range/seek) · `GET /recordings/{id}/poster` · `DELETE /recordings/{id}` |
| System | `GET /health` · `GET /system/info` · `GET/POST /videos` |

Full, interactive documentation is at `/docs` (Swagger UI) on a running backend.

## Project structure

```text
backend/
  app/
    main.py                 app, middleware, lifespan (DB connect, worker shutdown)
    api/                    HTTP routes (auth, cameras, detections, analytics, system)
    schemas/                Pydantic request/response models
    services/               business logic + MongoDB access
    cv/                     video_source, detector (YOLO+ByteTrack), line_counter, presence, recording_policy, clip_writer, annotate
    workers/                camera_worker (thread per camera), recorder, manager
    database/               async + sync clients, collections & indexes
    core/                   config, security (bcrypt/JWT), exceptions
  scripts/                  download_samples, seed_demo
  tests/
frontend/
  src/
    api/                    axios client + endpoint functions
    context/                AuthContext
    components/             layout, charts, live stream, line editor, forms
    pages/                  Dashboard, Live, Recordings, Cameras, Camera details, Analytics, History, Settings, auth
docs/DEPLOYMENT.md          Atlas + Render/VM + Vercel guide
docker-compose.yml · render.yaml · .github/workflows/ci.yml
```

## Deployment

MongoDB Atlas, a backend on Render / Railway / a VM (Docker, needs about 2 GB RAM for PyTorch), and the frontend on Vercel.
See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

## Credits

Sample videos: [Intel IoT DevKit sample-videos](https://github.com/intel-iot-devkit/sample-videos), CC-BY 4.0.
Detection model: [Ultralytics YOLO11](https://github.com/ultralytics/ultralytics) (AGPL-3.0).
