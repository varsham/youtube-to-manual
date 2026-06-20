"""
Video download and frame extraction service.
Uses yt-dlp for download and ffmpeg for frame extraction.
"""
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import yt_dlp

from app.config import settings


class VideoInfo:
    def __init__(self, title: str, duration: float, thumbnail: str, description: str):
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.description = description


class DownloadedVideo:
    def __init__(self, video_path: str, info: VideoInfo, transcript_segments: list[dict]):
        self.video_path = video_path
        self.info = info
        self.transcript_segments = transcript_segments


async def download_video(youtube_url: str, job_id: str) -> DownloadedVideo:
    """Download video and extract subtitles/captions."""
    frames_dir = settings.get_frames_path(job_id)
    video_path = os.path.join(frames_dir, "video.mp4")

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _download_sync, youtube_url, video_path, frames_dir)
    return result


_SIGN_IN_PHRASES = ("sign in", "log in", "age-restricted", "inappropriate", "confirm your age")

def _base_ydl_opts(video_path: str) -> dict:
    return {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best",
        "outtmpl": video_path,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "json3",
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "skip_download": False,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        # Enable Node.js as the JS runtime for YouTube's n-challenge solver.
        # yt-dlp defaults to deno-only; node is installed and must be opted in.
        "js_runtimes": {"node": {}},
    }


def _ydl_download(url: str, opts: dict) -> dict:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)


_MACOS_BROWSER_APPS = {
    "chrome": "/Applications/Google Chrome.app",
    "firefox": "/Applications/Firefox.app",
    "chromium": "/Applications/Chromium.app",
    "edge": "/Applications/Microsoft Edge.app",
    "brave": "/Applications/Brave Browser.app",
}


def _installed_browsers() -> list[str]:
    """Return browsers that are actually installed, Safari first on macOS."""
    import sys
    import os
    browsers = []
    if sys.platform == "darwin":
        browsers.append("safari")  # always present on macOS
        for name, path in _MACOS_BROWSER_APPS.items():
            if os.path.exists(path):
                browsers.append(name)
    else:
        browsers = ["chrome", "firefox", "chromium", "edge"]
    return browsers


def _ydl_download_with_cookies(url: str, opts: dict) -> dict:
    """Retry download using cookies from installed browsers."""
    browsers = _installed_browsers()
    if not browsers:
        raise RuntimeError(
            "This video requires a YouTube sign-in. "
            "No supported browsers found to read cookies from. "
            "Try a public video that does not require sign-in."
        )

    _COOKIES_NOT_FOUND = ("could not find", "cookies database", "no cookies", "keyring")

    tried = []
    for browser in browsers:
        try:
            cookie_opts = {**opts, "cookiesfrombrowser": (browser,)}
            with yt_dlp.YoutubeDL(cookie_opts) as ydl:
                return ydl.extract_info(url, download=True)
        except Exception as e:
            msg = str(e).lower()
            # Skip silently if the browser's cookie store simply doesn't exist
            if any(p in msg for p in _COOKIES_NOT_FOUND):
                continue
            tried.append(f"{browser}: {str(e)[:120]}")
            continue

    if tried:
        detail = "; ".join(tried)
        raise RuntimeError(
            f"This video requires YouTube authentication and no browser cookie "
            f"could unlock it ({detail}). "
            f"Make sure you are signed into YouTube in Safari or Chrome, "
            f"or try a public video that does not require sign-in."
        )
    raise RuntimeError(
        "This video requires YouTube sign-in. "
        "Sign into YouTube in Safari or Chrome, then retry. "
        "Alternatively, use a public video that does not require sign-in."
    )


def _download_sync(youtube_url: str, video_path: str, frames_dir: str) -> DownloadedVideo:
    opts = _base_ydl_opts(video_path)

    # If a cookies file is configured, use it directly — no browser guessing needed
    if settings.youtube_cookies_file:
        import os as _os
        if not _os.path.exists(settings.youtube_cookies_file):
            raise FileNotFoundError(
                f"YOUTUBE_COOKIES_FILE set to '{settings.youtube_cookies_file}' but file not found."
            )
        opts["cookiefile"] = settings.youtube_cookies_file

    try:
        info = _ydl_download(youtube_url, opts)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if "requested format is not available" in msg or "only images are available" in msg:
            raise RuntimeError(
                "This video has no downloadable video stream. YouTube has restricted it to "
                "thumbnails/storyboards only. Please try a different instructional video."
            )
        if any(p in msg for p in _SIGN_IN_PHRASES) and not settings.youtube_cookies_file:
            info = _ydl_download_with_cookies(youtube_url, opts)
        else:
            raise

    title = info.get("title", "Untitled")
    duration = float(info.get("duration", 0))
    thumbnail = info.get("thumbnail", "")
    description = info.get("description", "")[:1000]

    transcript_segments = _extract_transcript(frames_dir)

    return DownloadedVideo(
        video_path=video_path,
        info=VideoInfo(title=title, duration=duration, thumbnail=thumbnail, description=description),
        transcript_segments=transcript_segments,
    )


def _extract_transcript(frames_dir: str) -> list[dict]:
    """Extract transcript from downloaded subtitle files."""
    segments = []
    for fname in os.listdir(frames_dir):
        if fname.endswith(".json3") or fname.endswith(".vtt"):
            fpath = os.path.join(frames_dir, fname)
            try:
                if fname.endswith(".json3"):
                    segments = _parse_json3_subtitles(fpath)
                    break
                elif fname.endswith(".vtt"):
                    segments = _parse_vtt_subtitles(fpath)
                    break
            except Exception:
                continue
    return segments


def _parse_json3_subtitles(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    segments = []
    for event in data.get("events", []):
        if "segs" not in event:
            continue
        start_ms = event.get("tStartMs", 0)
        dur_ms = event.get("dDurationMs", 0)
        text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
        if text and text != "\n":
            segments.append({
                "start": start_ms / 1000.0,
                "end": (start_ms + dur_ms) / 1000.0,
                "text": text,
            })
    return segments


def _parse_vtt_subtitles(path: str) -> list[dict]:
    segments = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    i = 0
    while i < len(lines):
        if "-->" in lines[i]:
            parts = lines[i].split("-->")
            start = _vtt_time_to_seconds(parts[0].strip())
            end = _vtt_time_to_seconds(parts[1].strip().split()[0])
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            text = " ".join(text_lines)
            if text:
                segments.append({"start": start, "end": end, "text": text})
        else:
            i += 1
    return segments


def _vtt_time_to_seconds(t: str) -> float:
    parts = t.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def extract_frames(video_path: str, job_id: str, fps: float = 1.0) -> list[dict]:
    """
    Extract frames from video using ffmpeg.
    Returns list of {path, timestamp, index}.
    """
    frames_dir = settings.get_frames_path(job_id)
    frames_subdir = os.path.join(frames_dir, "frames")
    os.makedirs(frames_subdir, exist_ok=True)

    pattern = os.path.join(frames_subdir, "frame_%06d.jpg")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps},scale=640:-2",
        "-q:v", "3",
        "-y",
        pattern,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    frame_files = sorted(Path(frames_subdir).glob("frame_*.jpg"))
    frames = []
    for idx, fpath in enumerate(frame_files):
        timestamp = idx / fps
        frames.append({
            "path": str(fpath),
            "timestamp": timestamp,
            "index": idx,
        })

    return frames


def get_frame_at_timestamp(video_path: str, job_id: str, timestamp: float, suffix: str = "") -> str:
    """Extract a single frame at a specific timestamp."""
    frames_dir = settings.get_frames_path(job_id)
    out_path = os.path.join(frames_dir, f"frame_ts_{int(timestamp*1000)}{suffix}.jpg")

    cmd = [
        "ffmpeg", "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "3",
        "-y",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg single frame failed: {result.stderr}")
    return out_path
