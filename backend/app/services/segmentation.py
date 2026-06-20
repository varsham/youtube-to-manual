"""
Hybrid step boundary detection:
1. Frame difference analysis (pixel-level)
2. Transcript-based scene detection
3. LLM boundary validation (NVIDIA Nemotron)
"""
import asyncio
import os
from typing import Optional

import numpy as np
from PIL import Image
from scipy.signal import find_peaks
from scipy.signal.windows import gaussian


def _load_grayscale(path: str) -> np.ndarray:
    img = Image.open(path).convert("L").resize((160, 90))
    return np.array(img, dtype=np.float32)


def compute_frame_differences(frames: list[dict]) -> np.ndarray:
    """Compute normalized mean absolute difference between consecutive frames."""
    diffs = []
    prev = None
    for frame in frames:
        try:
            curr = _load_grayscale(frame["path"])
        except Exception:
            diffs.append(0.0)
            prev = None
            continue

        if prev is not None:
            diff = np.mean(np.abs(curr - prev))
            diffs.append(diff)
        else:
            diffs.append(0.0)
        prev = curr

    arr = np.array(diffs, dtype=np.float32)
    std = arr.std()
    if std > 0:
        arr = (arr - arr.mean()) / std
    return arr


def detect_boundaries_from_frames(
    frames: list[dict],
    min_segment_seconds: float = 8.0,
    max_segments: int = 20,
    fps: float = 1.0,
) -> list[float]:
    """
    Returns list of boundary timestamps (in seconds) using frame difference peaks.
    Always includes 0 and total_duration.
    """
    if len(frames) < 3:
        return [0.0, frames[-1]["timestamp"] if frames else 0.0]

    diffs = compute_frame_differences(frames)

    # Smooth with a small Gaussian kernel
    kernel_size = max(3, int(fps * 3))  # 3-second smoothing window
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = gaussian(kernel_size, std=kernel_size / 6)
    kernel /= kernel.sum()
    smoothed = np.convolve(diffs, kernel, mode="same")

    # Minimum distance between peaks: min_segment_seconds frames apart
    min_distance = max(1, int(min_segment_seconds * fps))

    peaks, properties = find_peaks(
        smoothed,
        height=0.3,
        distance=min_distance,
        prominence=0.2,
    )

    # Convert frame indices to timestamps
    total_duration = frames[-1]["timestamp"]
    boundary_times = [0.0]
    for p in peaks:
        t = frames[p]["timestamp"] if p < len(frames) else p / fps
        boundary_times.append(t)
    boundary_times.append(total_duration)

    # Merge segments that are too short
    boundary_times = _merge_short_segments(boundary_times, min_segment_seconds)

    # Cap at max_segments
    if len(boundary_times) - 1 > max_segments:
        boundary_times = _downsample_boundaries(boundary_times, max_segments)

    return boundary_times


def _merge_short_segments(boundaries: list[float], min_duration: float) -> list[float]:
    """Merge adjacent segments shorter than min_duration."""
    if len(boundaries) <= 2:
        return boundaries

    merged = [boundaries[0]]
    for b in boundaries[1:-1]:
        if b - merged[-1] >= min_duration:
            merged.append(b)
    merged.append(boundaries[-1])
    return merged


def _downsample_boundaries(boundaries: list[float], max_count: int) -> list[float]:
    """Keep only the strongest N-1 boundaries (plus start/end)."""
    interior = boundaries[1:-1]
    step = max(1, len(interior) // (max_count - 1))
    kept = interior[::step][:max_count - 1]
    return [boundaries[0]] + kept + [boundaries[-1]]


def detect_boundaries_from_transcript(
    transcript_segments: list[dict],
    total_duration: float,
    min_segment_seconds: float = 10.0,
) -> list[float]:
    """
    Detect boundaries from transcript pauses/topic shifts.
    Looks for gaps > 2s between subtitle segments as natural break points.
    """
    if not transcript_segments:
        return [0.0, total_duration]

    boundaries = [0.0]
    for i in range(1, len(transcript_segments)):
        gap = transcript_segments[i]["start"] - transcript_segments[i - 1]["end"]
        if gap > 2.0:
            candidate = (transcript_segments[i - 1]["end"] + transcript_segments[i]["start"]) / 2
            if candidate - boundaries[-1] >= min_segment_seconds:
                boundaries.append(candidate)

    if boundaries[-1] != total_duration:
        boundaries.append(total_duration)

    return boundaries


def merge_boundary_sources(
    frame_boundaries: list[float],
    transcript_boundaries: list[float],
    total_duration: float,
    tolerance: float = 3.0,
) -> list[float]:
    """
    Merge frame-based and transcript-based boundaries.
    Boundaries within `tolerance` seconds of each other are merged.
    """
    all_boundaries = set()
    all_boundaries.add(0.0)
    all_boundaries.add(total_duration)

    for b in frame_boundaries[1:-1]:
        all_boundaries.add(b)
    for b in transcript_boundaries[1:-1]:
        all_boundaries.add(b)

    sorted_b = sorted(all_boundaries)

    # Deduplicate close boundaries
    merged = [sorted_b[0]]
    for b in sorted_b[1:]:
        if b - merged[-1] > tolerance:
            merged.append(b)

    if merged[-1] != total_duration:
        merged.append(total_duration)

    return merged


def boundaries_to_segments(boundaries: list[float]) -> list[dict]:
    """Convert boundary list to segment dicts with start/end."""
    segments = []
    for i in range(len(boundaries) - 1):
        segments.append({
            "start": boundaries[i],
            "end": boundaries[i + 1],
        })
    return segments


def select_step_frames(
    frames: list[dict],
    segment_start: float,
    segment_end: float,
    fps: float = 1.0,
) -> dict:
    """
    Select BEFORE and AFTER frames for a segment.
    BEFORE: first 20% of segment
    AFTER: last 20% of segment

    Returns {before: frame_dict, after: frame_dict, candidates_before: [...], candidates_after: [...]}
    """
    duration = segment_end - segment_start
    before_window_end = segment_start + max(duration * 0.2, min(5.0, duration))
    after_window_start = segment_end - max(duration * 0.2, min(5.0, duration))

    segment_frames = [f for f in frames if segment_start <= f["timestamp"] < segment_end]

    if not segment_frames:
        return {"before": None, "after": None, "candidates_before": [], "candidates_after": []}

    before_candidates = [f for f in segment_frames if f["timestamp"] <= before_window_end]
    after_candidates = [f for f in segment_frames if f["timestamp"] >= after_window_start]

    before_frame = before_candidates[0] if before_candidates else segment_frames[0]
    after_frame = after_candidates[-1] if after_candidates else segment_frames[-1]

    # Avoid identical frames
    if before_frame["index"] == after_frame["index"] and len(segment_frames) > 1:
        after_frame = segment_frames[-1]

    return {
        "before": before_frame,
        "after": after_frame,
        "candidates_before": before_candidates[:5],
        "candidates_after": after_candidates[-5:],
    }


def get_transcript_for_segment(
    transcript_segments: list[dict],
    start: float,
    end: float,
) -> str:
    """Extract and join transcript text covering a time segment."""
    relevant = [
        t["text"]
        for t in transcript_segments
        if t["start"] < end and t.get("end", t["start"] + 1) > start
    ]
    return " ".join(relevant)[:1000]
