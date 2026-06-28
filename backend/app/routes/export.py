"""
Export endpoints: Markdown and PDF generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, Step, Frame
from app.services.export_service import generate_markdown, generate_pdf
from app.config import settings

router = APIRouter(prefix="/jobs/{job_id}/export", tags=["export"])


async def _load_job_and_steps(job_id: str, db: AsyncSession):
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status.value != "complete":
        raise HTTPException(status_code=400, detail="Job is not yet complete")

    steps_result = await db.execute(
        select(Step).where(Step.job_id == job_id).order_by(Step.order)
    )
    steps = steps_result.scalars().all()

    # Hydrate frame paths
    all_frame_ids = set()
    for s in steps:
        if s.before_frame_id:
            all_frame_ids.add(s.before_frame_id)
        if s.after_frame_id:
            all_frame_ids.add(s.after_frame_id)

    frame_map = {}
    if all_frame_ids:
        frames_result = await db.execute(
            select(Frame).where(Frame.id.in_(list(all_frame_ids)))
        )
        for f in frames_result.scalars().all():
            frame_map[f.id] = f

    steps_data = []
    for s in steps:
        before = frame_map.get(s.before_frame_id) if s.before_frame_id else None
        after = frame_map.get(s.after_frame_id) if s.after_frame_id else None
        steps_data.append({
            "id": s.id,
            "order": s.order,
            "title": s.title,
            "explanation": s.explanation,
            "checkpoint": s.checkpoint,
            "before_frame_id": s.before_frame_id,
            "after_frame_id": s.after_frame_id,
            "before_frame_path": before.file_path if before else None,
            "after_frame_path": after.file_path if after else None,
            "segment_start": s.segment_start,
            "segment_end": s.segment_end,
        })

    job_data = {
        "id": job.id,
        "video_title": job.video_title,
        "config": job.config,
    }

    return job_data, steps_data


@router.get("/markdown")
async def export_markdown(job_id: str, db: AsyncSession = Depends(get_db)):
    """Export steps as Markdown."""
    job_data, steps_data = await _load_job_and_steps(job_id, db)
    md = generate_markdown(job_data, steps_data, backend_url=settings.backend_url)
    filename = f"{job_data['video_title'] or 'manual'}.md"
    filename = "".join(c if c.isalnum() or c in "- _." else "_" for c in filename)
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
async def export_pdf(
    job_id: str,
    include_checkpoints: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """Export steps as PDF."""
    job_data, steps_data = await _load_job_and_steps(job_id, db)
    pdf_bytes = generate_pdf(
        job_data, steps_data,
        frames_dir_base=settings.frames_dir,
        include_checkpoints=include_checkpoints,
    )
    filename = f"{job_data['video_title'] or 'manual'}.pdf"
    filename = "".join(c if c.isalnum() or c in "- _." else "_" for c in filename)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
