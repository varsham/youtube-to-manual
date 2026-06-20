"""
FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db
from app.routes import jobs, steps, export


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    os.makedirs(settings.frames_dir, exist_ok=True)
    yield


app = FastAPI(
    title="YouTube to Manual",
    description="Convert YouTube instructional videos into structured step-by-step manuals",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(jobs.router, prefix="/api")
app.include_router(steps.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/frames/{job_id}/{frame_id}")
async def serve_frame(job_id: str, frame_id: str):
    """Serve extracted frame images."""
    from app.database import AsyncSessionLocal
    from app.models import Frame
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Frame).where(Frame.id == frame_id, Frame.job_id == job_id)
        )
        frame = result.scalar_one_or_none()

    if not frame or not os.path.exists(frame.file_path):
        raise HTTPException(status_code=404, detail="Frame not found")

    return FileResponse(frame.file_path, media_type="image/jpeg")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
