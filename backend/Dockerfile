# Build with the repo root as context, e.g.:
#   docker build -f backend/Dockerfile .          (production image, "runtime" target)
#   docker build -f backend/Dockerfile --target base .   (local dev, no frontend build)

# ---- Stage 1: build the frontend (only used by the "runtime" target) ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2 "base": backend + ffmpeg, no frontend baked in ----
# This is what local dev (docker-compose) uses - the frontend runs separately
# via its own hot-reload container, so building it here would be wasted work.
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN mkdir -p /app/frames

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- Stage 3 "runtime" (default): adds the built frontend ----
# Used for production (Render etc.), where one image serves both API and UI.
FROM base AS runtime
# main.py resolves the frontend build relative to the project root (one level
# above /app), so it must land at /frontend/dist to be picked up.
COPY --from=frontend-build /frontend/dist /frontend/dist
