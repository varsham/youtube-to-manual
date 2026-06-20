import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function formatTimestamp(seconds: number): string {
  return formatDuration(seconds);
}

export function extractVideoId(url: string): string | null {
  try {
    const u = new URL(url);
    if (u.hostname === "youtu.be") return u.pathname.slice(1).split("?")[0];
    return u.searchParams.get("v");
  } catch {
    return null;
  }
}

export function youtubeAtTime(url: string, seconds: number): string {
  const id = extractVideoId(url);
  if (!id) return url;
  return `https://www.youtube.com/watch?v=${id}&t=${Math.floor(seconds)}s`;
}

export function youtubeClipEmbed(url: string, start: number, end: number): string {
  const id = extractVideoId(url);
  if (!id) return url;
  return `https://www.youtube.com/embed/${id}?start=${Math.floor(start)}&end=${Math.floor(end)}&autoplay=1`;
}

export const STATUS_LABELS: Record<string, string> = {
  pending: "Queued",
  downloading: "Downloading video...",
  extracting_frames: "Extracting frames...",
  segmenting: "Detecting steps...",
  generating: "Generating content...",
  complete: "Complete",
  failed: "Failed",
};

export const STATUS_COLOR: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  downloading: "bg-blue-100 text-blue-700",
  extracting_frames: "bg-blue-100 text-blue-700",
  segmenting: "bg-violet-100 text-violet-700",
  generating: "bg-amber-100 text-amber-700",
  complete: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};
