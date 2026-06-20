"""
Celery tasks for async video processing pipeline.
"""
import asyncio
import os
import traceback
from datetime import datetime

from celery import Celery
from sqlalchemy import select, update

from app.config import settings

celery_app = Celery(
    "ytmanual",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, name="process_video", max_retries=2)
def process_video_task(self, job_id: str):
    """Main pipeline task: download → extract frames → segment → generate."""
    _run_async(_process_video_async(job_id))


async def run_pipeline(job_id: str):
    """Public entry point for running the pipeline without Celery context."""
    await _process_video_async(job_id)


async def _process_video_async(job_id: str):
    from app.database import AsyncSessionLocal
    from app.models import Job, JobStatus, Frame, Step, CorrectionStatus
    from app.services import video as video_svc
    from app.services import segmentation as seg_svc
    from app.services import ai_service

    async with AsyncSessionLocal() as db:
        try:
            # ── 1. Load job ──────────────────────────────────────────
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return

            config = job.config or {}
            youtube_url = job.youtube_url

            # ── 2. Download video ────────────────────────────────────
            await _set_status(db, job, JobStatus.downloading, 5.0)
            await _log(db, job, "Downloading video from YouTube...")
            downloaded = await video_svc.download_video(youtube_url, job_id)

            job.video_title = downloaded.info.title
            job.video_duration = downloaded.info.duration
            job.video_thumbnail = downloaded.info.thumbnail
            await db.commit()
            await _log(db, job, f'Video ready: "{downloaded.info.title}" ({downloaded.info.duration:.0f}s)')

            if downloaded.info.duration > settings.max_video_duration_seconds:
                raise ValueError(
                    f"Video too long: {downloaded.info.duration:.0f}s "
                    f"(max {settings.max_video_duration_seconds}s)"
                )

            # ── 3. Extract frames ────────────────────────────────────
            await _set_status(db, job, JobStatus.extracting_frames, 15.0)
            await _log(db, job, "Extracting frames from video...")
            fps = settings.max_frame_extraction_fps
            frames_data = video_svc.extract_frames(downloaded.video_path, job_id, fps=fps)
            await _log(db, job, f"Captured {len(frames_data)} frames")

            # Persist frames to DB
            db_frames = []
            for fd in frames_data:
                frame = Frame(
                    job_id=job_id,
                    timestamp=fd["timestamp"],
                    file_path=fd["path"],
                    frame_index=fd["index"],
                )
                db.add(frame)
                db_frames.append(frame)
            await db.commit()
            for f in db_frames:
                await db.refresh(f)

            # Build a lookup: timestamp → Frame ORM object
            frame_by_idx = {f.frame_index: f for f in db_frames}

            # ── 4. Detect step boundaries ────────────────────────────
            await _set_status(db, job, JobStatus.segmenting, 35.0)
            await _log(db, job, "Analysing video to find where each step begins and ends...")

            frame_boundaries = seg_svc.detect_boundaries_from_frames(
                frames_data,
                min_segment_seconds=8.0,
                max_segments=18,
                fps=fps,
            )
            transcript_boundaries = seg_svc.detect_boundaries_from_transcript(
                downloaded.transcript_segments,
                downloaded.info.duration,
                min_segment_seconds=10.0,
            )
            merged_boundaries = seg_svc.merge_boundary_sources(
                frame_boundaries, transcript_boundaries, downloaded.info.duration
            )
            segments = seg_svc.boundaries_to_segments(merged_boundaries)

            # ── 5. LLM boundary validation ──────────────────────────
            if segments and len(segments) > 2:
                await _log(db, job, f"Found {len(segments)} potential steps — refining boundaries with AI...")
                segments = await ai_service.validate_step_boundaries(
                    segments,
                    downloaded.info.title,
                    downloaded.transcript_segments,
                )
                await _log(db, job, f"Confirmed {len(segments)} steps")

            # ── 6. Generate step content ─────────────────────────────
            await _set_status(db, job, JobStatus.generating, 50.0)
            total_steps = len(segments)
            job.total_steps = total_steps
            await db.commit()
            await _log(db, job, f"Writing instructions for {total_steps} steps...")

            checkpoint_freq = config.get("checkpoint_frequency", "medium")
            checkpoint_every = {"low": 3, "medium": 1, "high": 1}[checkpoint_freq]

            for i, seg in enumerate(segments):
                progress = 50.0 + (i / total_steps) * 45.0
                await _set_status(db, job, JobStatus.generating, progress)

                # Select before/after frames
                frame_selection = seg_svc.select_step_frames(
                    frames_data, seg["start"], seg["end"], fps=fps
                )
                before_data = frame_selection["before"]
                after_data = frame_selection["after"]

                before_frame_db = frame_by_idx.get(before_data["index"]) if before_data else None
                after_frame_db = frame_by_idx.get(after_data["index"]) if after_data else None

                # Get transcript excerpt
                transcript_excerpt = seg_svc.get_transcript_for_segment(
                    downloaded.transcript_segments, seg["start"], seg["end"]
                )

                sparse = len((transcript_excerpt or "").strip()) < 60
                if sparse:
                    await _log(db, job, f"Step {i + 1} of {total_steps}: no speech detected — analysing visuals...")
                else:
                    await _log(db, job, f"Step {i + 1} of {total_steps}: writing instructions...")

                # Generate step content with LLM
                content = await ai_service.generate_step_content(
                    step_index=i,
                    total_steps=total_steps,
                    segment_start=seg["start"],
                    segment_end=seg["end"],
                    transcript_excerpt=transcript_excerpt,
                    video_title=downloaded.info.title,
                    config=config,
                    before_frame_path=before_data["path"] if before_data else None,
                    after_frame_path=after_data["path"] if after_data else None,
                )

                # Determine checkpoint: generate only per frequency setting
                checkpoint = ""
                if (i % checkpoint_every) == 0 or i == total_steps - 1:
                    checkpoint = content.get("checkpoint", "")

                # Build candidate frame id lists
                candidates_before = [
                    frame_by_idx[f["index"]].id
                    for f in frame_selection.get("candidates_before", [])
                    if f["index"] in frame_by_idx
                ]
                candidates_after = [
                    frame_by_idx[f["index"]].id
                    for f in frame_selection.get("candidates_after", [])
                    if f["index"] in frame_by_idx
                ]

                step = Step(
                    job_id=job_id,
                    order=i,
                    title=content.get("title", f"Step {i + 1}"),
                    explanation=content.get("explanation", ""),
                    checkpoint=checkpoint,
                    before_frame_id=before_frame_db.id if before_frame_db else None,
                    after_frame_id=after_frame_db.id if after_frame_db else None,
                    segment_start=seg["start"],
                    segment_end=seg["end"],
                    transcript_excerpt=transcript_excerpt[:500] if transcript_excerpt else None,
                    correction_status=CorrectionStatus.none,
                    candidate_before_frames=candidates_before,
                    candidate_after_frames=candidates_after,
                )
                db.add(step)

            # ── 7. Complete ──────────────────────────────────────────
            await _log(db, job, f"Done! Your manual has {total_steps} step{'s' if total_steps != 1 else ''}.")
            job.status = JobStatus.complete
            job.progress = 100.0
            job.updated_at = datetime.utcnow()
            await db.commit()

        except Exception as exc:
            tb = traceback.format_exc()
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.failed
                job.error_message = f"{str(exc)}\n\n{tb[:1000]}"
                job.updated_at = datetime.utcnow()
                await db.commit()
            raise


async def _set_status(db, job, status, progress: float):
    from app.models import JobStatus
    job.status = status
    job.progress = progress
    job.updated_at = datetime.utcnow()
    await db.commit()


async def _log(db, job, message: str):
    job.log_messages = list(job.log_messages or []) + [message]
    job.updated_at = datetime.utcnow()
    await db.commit()
