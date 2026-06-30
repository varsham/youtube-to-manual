# YouTube to Manual

Convert any YouTube instructional video into a structured, editable step-by-step manual with before/after images and AI-generated checkpoints.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Backend | FastAPI (Python 3.11), SQLAlchemy async, Celery |
| Queue | Redis |
| Database | PostgreSQL (or SQLite for local dev) |
| AI | NVIDIA Nemotron Ultra 253B via NIM API |
| Video | yt-dlp + ffmpeg |
| PDF | ReportLab |

## Quick Start (Docker)

```bash
cp .env.example .env
# Edit .env and set NVIDIA_API_KEY

docker-compose up
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Local Dev (no Docker)

**Prerequisites:** Python 3.11+, Node 20+, ffmpeg, Redis, PostgreSQL (or skip PG for SQLite)

```bash
# Backend
cd backend
pip install -r requirements.txt

# Use SQLite for zero-config local dev:
export DATABASE_URL="sqlite+aiosqlite:///./ytmanual.db"
export REDIS_URL="redis://localhost:6379/0"
export NVIDIA_API_KEY="nvapi-..."

# Terminal 1: API server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker
celery -A app.workers.tasks worker --loglevel=info
```

```bash
# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `NVIDIA_API_KEY` | NVIDIA NIM API key (required) |
| `NVIDIA_MODEL` | LLM model ID (default: `nvidia/nemotron-ultra-253b-v1`) |
| `NVIDIA_VISION_MODEL` | Vision model for frame descriptions |
| `DATABASE_URL` | SQLAlchemy async DB URL |
| `REDIS_URL` | Redis connection string |
| `FRAMES_DIR` | Where extracted frames are stored |
| `MAX_VIDEO_DURATION_SECONDS` | Max video length (default: 3600) |

## Pipeline

```
YouTube URL
    ↓
yt-dlp download (video + subtitles)
    ↓
ffmpeg frame extraction (1fps, 640px wide)
    ↓
Frame difference analysis (scipy peaks)
    +
Transcript gap detection
    ↓
Hybrid boundary merge
    ↓
NVIDIA Nemotron boundary validation
    ↓
Per-step content generation (title + explanation + checkpoint)
    ↓
Steps stored → served to UI
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jobs/` | Create job (submit URL + config) |
| GET | `/api/jobs/` | List jobs |
| GET | `/api/jobs/{id}` | Get job status |
| DELETE | `/api/jobs/{id}` | Delete job |
| GET | `/api/jobs/{id}/steps/` | Get all steps |
| POST | `/api/jobs/{id}/steps/{sid}/rewrite` | Rewrite step |
| POST | `/api/jobs/{id}/steps/{sid}/request-image` | Cycle to next frame |
| POST | `/api/jobs/{id}/steps/{sid}/suggest-correction` | AI analyze step |
| POST | `/api/jobs/{id}/steps/{sid}/apply-correction` | Apply/reject suggestion |
| POST | `/api/jobs/{id}/steps/analyze-all` | AI analyze all steps |
| GET | `/api/jobs/{id}/export/markdown` | Export as Markdown |
| GET | `/api/jobs/{id}/export/pdf` | Export as PDF |

## Deploying

FastAPI serves the built frontend directly, so the whole app is one
deployable unit:

```bash
cd frontend && npm run build   # outputs frontend/dist
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`backend/Procfile` defines two process types — deploy both:

- `web` — the FastAPI app above (serves the API and the built frontend)
- `worker` — the Celery worker that runs the actual pipeline jobs

You'll also need a Redis instance for `REDIS_URL` and a Postgres database
for `DATABASE_URL` (SQLite works for local dev but isn't safe for a
multi-process deploy). One free/cheap option that maps directly onto this
Procfile: [Render](https://render.com) — create a Web Service for `web`,
a Background Worker for `worker`, both pointed at this repo with build
command `cd frontend && npm install && npm run build && cd ../backend && pip
install -r requirements.txt`, plus a managed Redis and Postgres instance.
Render gives you one URL for the web service — that's the link to share.

## Getting an NVIDIA API Key

1. Go to https://integrate.api.nvidia.com
2. Sign in / create account
3. Generate an API key under "API Keys"
4. Set `NVIDIA_API_KEY=nvapi-...` in your `.env`
