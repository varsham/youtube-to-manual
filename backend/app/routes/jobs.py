"""
Job CRUD endpoints: create, status poll, list.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Job, JobStatus, Step, Frame

router = APIRouter(prefix="/jobs", tags=["jobs"])


class UserConfig(BaseModel):
    experience_level: str = "intermediate"  # beginner | intermediate | expert
    explanation_style: str = "detailed"      # simple | detailed | technical | analogies
    checkpoint_frequency: str = "medium"      # low | medium | high
    screenshots_per_step: int = 2
    user_skills: str = ""

    @field_validator("experience_level")
    @classmethod
    def validate_level(cls, v):
        assert v in ("beginner", "intermediate", "expert"), "invalid level"
        return v

    @field_validator("explanation_style")
    @classmethod
    def validate_style(cls, v):
        assert v in ("simple", "detailed", "technical", "analogies"), "invalid style"
        return v

    @field_validator("checkpoint_frequency")
    @classmethod
    def validate_freq(cls, v):
        assert v in ("low", "medium", "high"), "invalid frequency"
        return v


class CreateJobRequest(BaseModel):
    youtube_url: str
    config: UserConfig = UserConfig()

    @field_validator("youtube_url")
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if "youtube.com" not in v and "youtu.be" not in v:
            raise ValueError("Must be a YouTube URL")
        return v


class FrameResponse(BaseModel):
    id: str
    timestamp: float
    url: str

    class Config:
        from_attributes = True


class StepSummary(BaseModel):
    id: str
    order: int
    title: str
    checkpoint: str
    correction_status: str

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    id: str
    youtube_url: str
    status: str
    video_title: Optional[str]
    video_duration: Optional[float]
    video_thumbnail: Optional[str]
    total_steps: int
    progress: float
    error_message: Optional[str]
    config: dict
    created_at: str

    class Config:
        from_attributes = True


def _job_to_response(job: Job) -> dict:
    status = job.status
    status_str = status.value if hasattr(status, "value") else str(status)
    return {
        "id": job.id,
        "youtube_url": job.youtube_url,
        "status": status_str,
        "video_title": job.video_title,
        "video_duration": job.video_duration,
        "video_thumbnail": job.video_thumbnail,
        "total_steps": job.total_steps,
        "progress": job.progress,
        "log_messages": job.log_messages or [],
        "error_message": job.error_message,
        "config": job.config,
        "created_at": job.created_at.isoformat(),
    }


@router.post("/", status_code=201)
async def create_job(
    body: CreateJobRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new processing job and enqueue it."""
    import asyncio

    job = Job(
        id=str(uuid.uuid4()),
        youtube_url=body.youtube_url,
        config=body.config.model_dump(),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Try Celery first; fall back to a direct asyncio task if Redis is unavailable
    celery_dispatched = False
    try:
        from app.workers.tasks import process_video_task
        task = process_video_task.delay(job.id)
        job.celery_task_id = task.id
        await db.commit()
        celery_dispatched = True
    except Exception:
        pass  # Redis not running — use in-process fallback below

    if not celery_dispatched:
        from app.workers.tasks import run_pipeline
        asyncio.create_task(run_pipeline(job.id))

    return _job_to_response(job)


@router.get("/")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """List all jobs, newest first."""
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).limit(50)
    )
    jobs = result.scalars().all()
    return [_job_to_response(j) for j in jobs]


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job status and metadata."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job and all associated data."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()
