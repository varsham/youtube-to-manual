"""
NVIDIA Nemotron-based AI service.
All public functions degrade gracefully when the API key is missing or the call fails.
"""
import base64
import json
import logging
import os
import textwrap
from typing import Optional

from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def ai_enabled() -> bool:
    return bool(settings.nvidia_api_key)


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key or "no-key",
        )
    return _client


async def _chat(messages: list[dict], max_tokens: int = 800, temperature: float = 0.3) -> str:
    """Call NVIDIA API and return raw text. Raises on any error."""
    response = await get_client().chat.completions.create(
        model=settings.nvidia_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def _parse_json(raw: str):
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _build_user_context(config: dict) -> str:
    level = config.get("experience_level", "intermediate")
    style = config.get("explanation_style", "detailed")
    skills = config.get("user_skills", "")
    freq = config.get("checkpoint_frequency", "medium")
    ctx = f"The user is a {level} learner who prefers {style} explanations."
    if skills:
        ctx += f" Their background: {skills}."
    ctx += f" Checkpoint frequency: {freq}."
    return ctx


# ── Fallback helpers (no AI) ─────────────────────────────────────────────────

def _fallback_step_content(step_index: int, total_steps: int, transcript_excerpt: str, visual_description: str = "") -> dict:
    context = transcript_excerpt or visual_description
    sentences = [s.strip() for s in context.replace("\n", " ").split(".") if s.strip()]
    title_src = sentences[0] if sentences else f"Step {step_index + 1}"
    title = textwrap.shorten(title_src, width=60, placeholder="...")
    explanation = context if context else f"Step {step_index + 1} of the procedure."
    return {
        "title": title or f"Step {step_index + 1}",
        "explanation": explanation,
        "checkpoint": (
            "You have completed this section. Review what you just did before continuing."
            if step_index < total_steps - 1
            else "You have reached the end of the procedure. Verify the final result."
        ),
    }


async def _describe_frames_visually(
    before_path: Optional[str],
    after_path: Optional[str],
    video_title: str,
) -> str:
    """Call vision model on before/after frames to describe the action taking place."""
    images = []
    for path in [before_path, after_path]:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            images.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

    if not images:
        return ""

    content = images + [{"type": "text", "text": (
        f'These are frames from an instructional video titled "{video_title}". '
        "Describe in 2-3 sentences exactly what procedural action is being demonstrated — "
        "be specific about what is shown (tools, materials, hand movements, on-screen actions, etc.). "
        "Do not say 'the video shows'; just describe the action directly."
    )}]

    try:
        response = await get_client().chat.completions.create(
            model=settings.nvidia_vision_model,
            messages=[{"role": "user", "content": content}],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("_describe_frames_visually failed (%s)", e)
        return ""


# ── Public API ───────────────────────────────────────────────────────────────

async def generate_step_content(
    step_index: int,
    total_steps: int,
    segment_start: float,
    segment_end: float,
    transcript_excerpt: str,
    video_title: str,
    config: dict,
    before_frame_path: Optional[str] = None,
    after_frame_path: Optional[str] = None,
) -> dict:
    # When transcript is sparse, get a visual description from the frame images
    visual_description = ""
    transcript_is_sparse = len((transcript_excerpt or "").strip()) < 60
    if transcript_is_sparse and ai_enabled():
        visual_description = await _describe_frames_visually(
            before_frame_path, after_frame_path, video_title
        )

    if not ai_enabled():
        return _fallback_step_content(step_index, total_steps, transcript_excerpt, visual_description)

    user_ctx = _build_user_context(config)
    duration = segment_end - segment_start

    if transcript_is_sparse and visual_description:
        content_source = f"Visual description of frames:\n{visual_description}"
    elif transcript_excerpt:
        content_source = f"Transcript:\n{transcript_excerpt}"
    else:
        content_source = "(no transcript or visual description available)"

    prompt = f"""You are generating structured instructional content for a step-by-step manual.

Video: "{video_title}"
Step {step_index + 1} of {total_steps}
Time range: {segment_start:.1f}s – {segment_end:.1f}s (duration: {duration:.1f}s)

{content_source}

User context: {user_ctx}

Write a clear, actionable explanation of what the viewer should do or observe at this point.
If only visual information is available, describe what is happening based on what can be seen.

Return only this JSON (no markdown fences):
{{
  "title": "Short imperative title (max 8 words)",
  "explanation": "Step-by-step explanation adapted to the user's level.",
  "checkpoint": "Specific, observable outcome the user can verify."
}}"""

    try:
        raw = await _chat([
            {"role": "system", "content": "You are an expert technical writer. Respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ], max_tokens=800)
        return _parse_json(raw)
    except Exception as e:
        logger.warning("generate_step_content failed (%s), using fallback", e)
        return _fallback_step_content(step_index, total_steps, transcript_excerpt, visual_description)


async def rewrite_step(
    current_explanation: str,
    rewrite_instruction: str,
    config: dict,
    title: str,
) -> dict:
    if not ai_enabled():
        return {"explanation": current_explanation, "checkpoint": ""}

    user_ctx = _build_user_context(config)
    prompt = f"""Rewrite this instructional step.

Title: "{title}"
Current explanation:
---
{current_explanation}
---
Instruction: "{rewrite_instruction}"
User context: {user_ctx}

Return only JSON (no markdown):
{{"explanation": "...", "checkpoint": "..."}}"""

    try:
        raw = await _chat([
            {"role": "system", "content": "You rewrite instructional content. Respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ], max_tokens=600, temperature=0.4)
        return _parse_json(raw)
    except Exception as e:
        logger.warning("rewrite_step failed (%s), returning original", e)
        return {"explanation": current_explanation, "checkpoint": ""}


async def validate_step_boundaries(
    segments: list[dict],
    video_title: str,
    transcript_segments: list[dict],
) -> list[dict]:
    """LLM-validate step boundaries. Returns original segments on any failure."""
    if not ai_enabled():
        return segments

    segment_summary = []
    for i, seg in enumerate(segments):
        transcript = " ".join(
            t["text"]
            for t in transcript_segments
            if seg["start"] <= t.get("start", 0) < seg["end"]
        )[:300]
        segment_summary.append(
            f"Segment {i+1}: {seg['start']:.1f}s–{seg['end']:.1f}s | {transcript or '(no transcript)'}"
        )

    prompt = f"""Validate step boundaries for a procedural instructional video.

Video: "{video_title}"
Proposed segments:
{chr(10).join(segment_summary)}

Rules:
- Each step = ONE distinct procedural action
- Merge steps shorter than 10s into adjacent ones
- Split steps longer than 120s that cover multiple actions
- Keep the intro step
- Target 4–15 steps total

Return only a JSON array (no markdown):
[{{"start": 0.0, "end": 15.0, "rationale": "..."}}]"""

    try:
        raw = await _chat([
            {"role": "system", "content": "You validate procedural step boundaries. Respond with a JSON array only."},
            {"role": "user", "content": prompt},
        ], max_tokens=1200, temperature=0.2)
        validated = _parse_json(raw)
        if isinstance(validated, list) and len(validated) > 0:
            return validated
    except Exception as e:
        logger.warning("validate_step_boundaries failed (%s), keeping original segments", e)

    return segments


async def analyze_steps_for_corrections(
    steps: list[dict],
    video_title: str,
    config: dict,
) -> list[dict]:
    if not ai_enabled():
        return []

    steps_text = [
        f"Step {i+1} (id={s['id']}): [{s['title']}] "
        f"duration={s.get('segment_end', 0) - s.get('segment_start', 0):.0f}s\n"
        f"  {s['explanation'][:200]}"
        for i, s in enumerate(steps)
    ]

    prompt = f"""QA review for an instructional manual converted from a video.

Video: "{video_title}"
Steps:
{chr(10).join(steps_text)}

Return a JSON array of issues (empty array if none):
[{{
  "step_id": "uuid",
  "issue_type": "too_broad|too_narrow|unclear_boundary|explanation_quality",
  "description": "...",
  "proposed_action": "split|merge|rewrite",
  "proposed_detail": "..."
}}]"""

    try:
        raw = await _chat([
            {"role": "system", "content": "You QA-review instructional manuals. Return JSON only."},
            {"role": "user", "content": prompt},
        ], max_tokens=1500, temperature=0.3)
        result = _parse_json(raw)
        if isinstance(result, list):
            return result
    except Exception as e:
        logger.warning("analyze_steps_for_corrections failed (%s)", e)

    return []


async def describe_frame_for_context(image_path: str) -> str:
    if not ai_enabled() or not os.path.exists(image_path):
        return ""

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    try:
        response = await get_client().chat.completions.create(
            model=settings.nvidia_vision_model,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": "Describe what is happening in this instructional video frame in one sentence."},
            ]}],
            max_tokens=100,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("describe_frame_for_context failed (%s)", e)
        return ""
