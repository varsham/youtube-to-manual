import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, ForeignKey,
    Enum as SAEnum, JSON, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class JobStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    extracting_frames = "extracting_frames"
    segmenting = "segmenting"
    generating = "generating"
    complete = "complete"
    failed = "failed"


class CorrectionStatus(str, enum.Enum):
    none = "none"
    suggested = "suggested"
    approved = "approved"
    rejected = "rejected"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    youtube_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.pending, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    video_title: Mapped[Optional[str]] = mapped_column(String(500))
    video_duration: Mapped[Optional[float]] = mapped_column(Float)
    video_thumbnail: Mapped[Optional[str]] = mapped_column(String(500))
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    log_messages: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps: Mapped[list["Step"]] = relationship(
        "Step", back_populates="job", cascade="all, delete-orphan", order_by="Step.order"
    )
    frames: Mapped[list["Frame"]] = relationship(
        "Frame", back_populates="job", cascade="all, delete-orphan"
    )


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500))
    frame_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["Job"] = relationship("Job", back_populates="frames")


class Step(Base):
    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    checkpoint: Mapped[str] = mapped_column(Text, default="")
    before_frame_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("frames.id"))
    after_frame_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("frames.id"))
    segment_start: Mapped[Optional[float]] = mapped_column(Float)
    segment_end: Mapped[Optional[float]] = mapped_column(Float)
    transcript_excerpt: Mapped[Optional[str]] = mapped_column(Text)
    correction_status: Mapped[CorrectionStatus] = mapped_column(
        SAEnum(CorrectionStatus), default=CorrectionStatus.none
    )
    correction_suggestion: Mapped[Optional[dict]] = mapped_column(JSON)
    candidate_before_frames: Mapped[Optional[list]] = mapped_column(JSON)
    candidate_after_frames: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job: Mapped["Job"] = relationship("Job", back_populates="steps")
    before_frame: Mapped[Optional["Frame"]] = relationship("Frame", foreign_keys=[before_frame_id])
    after_frame: Mapped[Optional["Frame"]] = relationship("Frame", foreign_keys=[after_frame_id])
