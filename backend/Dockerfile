# Build with the repo root as context, e.g.:
#   docker build -f backend/Dockerfile .

# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend runtime, with ffmpeg for video processing ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# main.py resolves the frontend build relative to the project root (one level
# above /app), so it must land at /frontend/dist to be picked up.
COPY --from=frontend-build /frontend/dist /frontend/dist

RUN mkdir -p /app/frames

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
