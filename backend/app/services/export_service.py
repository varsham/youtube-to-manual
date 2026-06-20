"""
Export service: generates Markdown and PDF from job steps.
"""
import base64
import io
import os
from datetime import datetime
from typing import Optional

import markdown2
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def generate_markdown(job: dict, steps: list[dict], backend_url: str) -> str:
    """Generate Markdown export from job and steps."""
    lines = []
    title = job.get("video_title", "Untitled")
    config = job.get("config", {})

    lines.append(f"# {title}")
    lines.append(f"\n*Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*")
    lines.append(f"\n**Experience level:** {config.get('experience_level', 'intermediate').title()}  ")
    lines.append(f"**Explanation style:** {config.get('explanation_style', 'detailed').title()}  ")
    lines.append(f"\n---\n")

    for i, step in enumerate(steps):
        lines.append(f"## Step {i + 1}: {step['title']}")

        before_id = step.get("before_frame_id")
        after_id = step.get("after_frame_id")

        if before_id or after_id:
            lines.append("\n| Before | After |")
            lines.append("|--------|-------|")
            before_url = f"{backend_url}/frames/{job['id']}/{before_id}" if before_id else ""
            after_url = f"{backend_url}/frames/{job['id']}/{after_id}" if after_id else ""
            lines.append(f"| ![]({before_url}) | ![]({after_url}) |")

        lines.append(f"\n{step['explanation']}")

        if step.get("checkpoint"):
            lines.append(f"\n> **Checkpoint:** {step['checkpoint']}")

        if i < len(steps) - 1:
            lines.append("\n---\n")

    return "\n".join(lines)


def generate_pdf(job: dict, steps: list[dict], frames_dir_base: str) -> bytes:
    """Generate PDF from job steps using reportlab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontSize=18, spaceAfter=12
    )
    heading_style = ParagraphStyle(
        "Heading1", parent=styles["Heading1"], fontSize=14, spaceAfter=6, spaceBefore=12
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, spaceAfter=6, leading=14
    )
    checkpoint_style = ParagraphStyle(
        "Checkpoint", parent=styles["Normal"], fontSize=10, spaceAfter=6,
        leftIndent=12, borderPad=6, backColor=colors.lightblue,
        leading=14
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=12
    )

    story = []
    title = job.get("video_title", "Untitled")
    config = job.get("config", {})

    story.append(Paragraph(title, title_style))
    story.append(Paragraph(
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
        f"Level: {config.get('experience_level', 'intermediate').title()} | "
        f"Style: {config.get('explanation_style', 'detailed').title()}",
        meta_style
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 12))

    job_frames_dir = os.path.join(frames_dir_base, job["id"])

    for i, step in enumerate(steps):
        step_elements = []
        step_elements.append(Paragraph(f"Step {i + 1}: {step['title']}", heading_style))

        before_id = step.get("before_frame_id")
        after_id = step.get("after_frame_id")
        before_path = step.get("before_frame_path")
        after_path = step.get("after_frame_path")

        if before_path and after_path and os.path.exists(before_path) and os.path.exists(after_path):
            max_w = (doc.width / 2) - 6
            max_h = 1.8 * inch

            try:
                before_img = _fit_image(before_path, max_w, max_h)
                after_img = _fit_image(after_path, max_w, max_h)
                from reportlab.platypus import Table, TableStyle
                img_table = Table(
                    [[before_img, after_img]],
                    colWidths=[max_w + 6, max_w + 6],
                )
                img_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ]))
                step_elements.append(img_table)
                step_elements.append(Spacer(1, 6))

                from reportlab.platypus import Table as LabelTable, TableStyle as LTS
                label_table = LabelTable(
                    [[Paragraph("Before", meta_style), Paragraph("After", meta_style)]],
                    colWidths=[max_w + 6, max_w + 6],
                )
                label_table.setStyle(LTS([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
                step_elements.append(label_table)
            except Exception:
                pass

        explanation = step.get("explanation", "").replace("\n", "<br/>")
        step_elements.append(Paragraph(explanation, body_style))

        if step.get("checkpoint"):
            checkpoint_text = f"<b>Checkpoint:</b> {step['checkpoint']}"
            step_elements.append(Paragraph(checkpoint_text, checkpoint_style))

        step_elements.append(Spacer(1, 8))
        step_elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        step_elements.append(Spacer(1, 4))

        story.append(KeepTogether(step_elements[:4]))
        for el in step_elements[4:]:
            story.append(el)

    doc.build(story)
    return buf.getvalue()


def _fit_image(path: str, max_width: float, max_height: float) -> RLImage:
    from PIL import Image
    with Image.open(path) as img:
        w, h = img.size

    ratio = min(max_width / w, max_height / h)
    return RLImage(path, width=w * ratio, height=h * ratio)
