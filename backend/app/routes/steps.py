"""
Step endpoints: read, rewrite, correction workflow, image re-selection.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database import get_db
from app.models import Job, Step, Frame, CorrectionStatus
from app.config import settings

router = APIRouter(prefix="/jobs/{job_id}/steps", tags=["steps"])


def _frame_url(frame: Optional[Frame], job_id: str, request_base: str = "") -> Optional[str]:
    if not frame:
        return None
    return f"/frames/{job_id}/{frame.id}"


def _step_to_dict(step: Step, job_id: str) -> dict:
    return {
        "id": step.id,
        "order": step.order,
        "title": step.title,
        "explanation": step.explanation,
        "checkpoint": step.checkpoint,
        "before_frame_id": step.before_frame_id,
        "after_frame_id": step.after_frame_id,
        "before_frame_url": f"/frames/{job_id}/{step.before_frame_id}" if step.before_frame_id else None,
        "after_frame_url": f"/frames/{job_id}/{step.after_frame_id}" if step.after_frame_id else None,
        "segment_start": step.segment_start,
        "segment_end": step.segment_end,
        "correction_status": step.correction_status.value,
        "correction_suggestion": step.correction_suggestion,
        "candidate_before_frames": step.candidate_before_frames or [],
        "candidate_after_frames": step.candidate_after_frames or [],
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
    }


@router.get("/")
async def list_steps(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get all steps for a job, ordered."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(Step).where(Step.job_id == job_id).order_by(Step.order)
    )
    steps = result.scalars().all()
    return [_step_to_dict(s, job_id) for s in steps]


@router.get("/{step_id}")
async def get_step(job_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Step).where(Step.id == step_id, Step.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return _step_to_dict(step, job_id)


class EditStepRequest(BaseModel):
    title: Optional[str] = None
    explanation: Optional[str] = None
    checkpoint: Optional[str] = None


@router.patch("/{step_id}")
async def edit_step(
    job_id: str,
    step_id: str,
    body: EditStepRequest,
    db: AsyncSession = Depends(get_db),
):
    """Directly edit a step's title, explanation, or checkpoint."""
    result = await db.execute(
        select(Step).where(Step.id == step_id, Step.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    if body.title is not None:
        step.title = body.title
    if body.explanation is not None:
        step.explanation = body.explanation
    if body.checkpoint is not None:
        step.checkpoint = body.checkpoint
    step.updated_at = datetime.utcnow()
    await db.commit()
    return _step_to_dict(step, job_id)


class RewriteRequest(BaseModel):
    instruction: str


@router.post("/{step_id}/rewrite")
async def rewrite_step(
    job_id: str,
    step_id: str,
    body: RewriteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rewrite a single step's explanation via LLM."""
    from app.services.ai_service import rewrite_step as ai_rewrite

    result = await db.execute(
        select(Step).where(Step.id == step_id, Step.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Map shorthand instructions to full prompts
    instruction_map = {
        "simpler": "Rewrite this explanation in much simpler terms. Use plain language, short sentences, and avoid jargon. Add helpful analogies if useful.",
        "detailed": "Rewrite this explanation with more detail. Add sub-steps, explain the WHY behind each action, and include any common pitfalls to watch for.",
        "technical": "Rewrite this explanation in precise technical language. Use exact terminology, include relevant technical details, command names, or specifications.",
        "analogies": "Rewrite this explanation using everyday analogies to make the concepts intuitive. Keep technical accuracy but use relatable comparisons.",
    }
    full_instruction = instruction_map.get(body.instruction, body.instruction)

    rewritten = await ai_rewrite(
        current_explanation=step.explanation,
        rewrite_instruction=full_instruction,
        config=job.config or {},
        title=step.title,
    )

    step.explanation = rewritten.get("explanation", step.explanation)
    if rewritten.get("checkpoint"):
        step.checkpoint = rewritten["checkpoint"]
    step.updated_at = datetime.utcnow()
    await db.commit()

    return _step_to_dict(step, job_id)


@router.post("/{step_id}/request-image")
async def request_different_image(
    job_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate to next candidate before/after frame pair for this step.
    Cycles through the candidate list.
    """
    result = await db.execute(
        select(Step).where(Step.id == step_id, Step.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    candidates_before = step.candidate_before_frames or []
    candidates_after = step.candidate_after_frames or []

    if not candidates_before and not candidates_after:
        raise HTTPException(status_code=400, detail="No alternative frames available for this step")

    # Find next before frame
    if candidates_before and step.before_frame_id in candidates_before:
        idx = candidates_before.index(step.before_frame_id)
        next_before = candidates_before[(idx + 1) % len(candidates_before)]
    elif candidates_before:
        next_before = candidates_before[0]
    else:
        next_before = step.before_frame_id

    # Find next after frame
    if candidates_after and step.after_frame_id in candidates_after:
        idx = candidates_after.index(step.after_frame_id)
        next_after = candidates_after[(idx + 1) % len(candidates_after)]
    elif candidates_after:
        next_after = candidates_after[-1]
    else:
        next_after = step.after_frame_id

    step.before_frame_id = next_before
    step.after_frame_id = next_after
    step.updated_at = datetime.utcnow()
    await db.commit()

    return _step_to_dict(step, job_id)


@router.post("/{step_id}/suggest-correction")
async def suggest_correction(
    job_id: str,
    step_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI analysis for a single step and store suggestion."""
    from app.services.ai_service import analyze_steps_for_corrections

    result = await db.execute(
        select(Step).where(Step.id == step_id, Step.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()

    suggestions = await analyze_steps_for_corrections(
        steps=[{
            "id": step.id,
            "title": step.title,
            "explanation": step.explanation,
            "segment_start": step.segment_start or 0,
            "segment_end": step.segment_end or 0,
        }],
        video_title=job.video_title or "",
        config=job.config or {},
    )

    if suggestions:
        step.correction_suggestion = suggestions[0]
        step.correction_status = CorrectionStatus.suggested
    else:
        step.correction_suggestion = {"message": "No issues detected in this step."}
        step.correction_status = CorrectionStatus.suggested

    step.updated_at = datetime.utcnow()
    await db.commit()
    return _step_to_dict(step, job_id)


class ApplyCorrectionRequest(BaseModel):
    action: str  # "approve_split" | "approve_merge" | "reject" | "approve_rewrite"
    merge_with_step_id: Optional[str] = None


@router.post("/{step_id}/apply-correction")
async def apply_correction(
    job_id: str,
    step_id: str,
    body: ApplyCorrectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """User approves or rejects the AI correction suggestion."""
    result = await db.execute(
        select(Step).where(Step.id == step_id, Step.job_id == job_id)
    )
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    if body.action == "reject":
        step.correction_status = CorrectionStatus.rejected
        step.correction_suggestion = None
        step.updated_at = datetime.utcnow()
        await db.commit()
        return _step_to_dict(step, job_id)

    suggestion = step.correction_suggestion or {}
    proposed_action = suggestion.get("proposed_action", "")

    if body.action == "approve_rewrite":
        # Just clear the suggestion; rewrite is done separately
        step.correction_status = CorrectionStatus.approved
        step.correction_suggestion = None

    elif body.action == "approve_split" and proposed_action == "split":
        # Split this step into two at midpoint
        mid = ((step.segment_start or 0) + (step.segment_end or 0)) / 2

        # Get candidate frames near midpoint
        all_steps_result = await db.execute(
            select(Step).where(Step.job_id == job_id).order_by(Step.order)
        )
        all_steps = all_steps_result.scalars().all()

        # Create new step at order + 1, shift others
        for s in all_steps:
            if s.order > step.order:
                s.order += 1

        import uuid as _uuid
        new_step = Step(
            id=str(_uuid.uuid4()),
            job_id=job_id,
            order=step.order + 1,
            title=f"{step.title} (continued)",
            explanation=step.explanation,
            checkpoint=step.checkpoint,
            before_frame_id=step.after_frame_id,
            after_frame_id=step.after_frame_id,
            segment_start=mid,
            segment_end=step.segment_end,
            correction_status=CorrectionStatus.none,
        )
        step.segment_end = mid
        step.correction_status = CorrectionStatus.approved
        step.correction_suggestion = None
        db.add(new_step)

    elif body.action == "approve_merge" and body.merge_with_step_id:
        # Merge two adjacent steps
        result2 = await db.execute(
            select(Step).where(Step.id == body.merge_with_step_id, Step.job_id == job_id)
        )
        other = result2.scalar_one_or_none()
        if other:
            # Keep current step, extend to cover other's range
            step.segment_end = max(step.segment_end or 0, other.segment_end or 0)
            step.explanation += "\n\n" + other.explanation
            step.after_frame_id = other.after_frame_id
            step.correction_status = CorrectionStatus.approved
            step.correction_suggestion = None

            # Re-order remaining steps
            all_steps_result = await db.execute(
                select(Step).where(Step.job_id == job_id).order_by(Step.order)
            )
            all_steps = all_steps_result.scalars().all()
            await db.delete(other)
            remaining = [s for s in all_steps if s.id != other.id]
            for idx, s in enumerate(sorted(remaining, key=lambda x: x.order)):
                s.order = idx

    step.updated_at = datetime.utcnow()
    await db.commit()

    # Return all steps so UI can re-render
    steps_result = await db.execute(
        select(Step).where(Step.job_id == job_id).order_by(Step.order)
    )
    all_steps = steps_result.scalars().all()
    return [_step_to_dict(s, job_id) for s in all_steps]


@router.post("/analyze-all")
async def analyze_all_steps(job_id: str, db: AsyncSession = Depends(get_db)):
    """Run AI correction analysis on all steps of a job."""
    from app.services.ai_service import analyze_steps_for_corrections

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    steps_result = await db.execute(
        select(Step).where(Step.job_id == job_id).order_by(Step.order)
    )
    steps = steps_result.scalars().all()

    steps_data = [
        {
            "id": s.id,
            "title": s.title,
            "explanation": s.explanation,
            "segment_start": s.segment_start or 0,
            "segment_end": s.segment_end or 0,
        }
        for s in steps
    ]

    suggestions = await analyze_steps_for_corrections(
        steps=steps_data,
        video_title=job.video_title or "",
        config=job.config or {},
    )

    # Map suggestions back to steps
    suggestion_map = {s["step_id"]: s for s in suggestions}
    for step in steps:
        if step.id in suggestion_map:
            step.correction_suggestion = suggestion_map[step.id]
            step.correction_status = CorrectionStatus.suggested
            step.updated_at = datetime.utcnow()

    await db.commit()
    return [_step_to_dict(s, job_id) for s in steps]
