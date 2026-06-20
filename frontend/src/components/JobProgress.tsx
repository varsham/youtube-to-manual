import { useEffect, useRef } from "react";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { AlertCircle, CheckCircle2, Loader2, Clock } from "lucide-react";
import { STATUS_LABELS, STATUS_COLOR, formatDuration } from "../lib/utils";
import type { Job } from "../types";

interface Props {
  job: Job;
}

const STEPS_PIPELINE = [
  { key: "downloading", label: "Download" },
  { key: "extracting_frames", label: "Frames" },
  { key: "segmenting", label: "Segment" },
  { key: "generating", label: "Generate" },
  { key: "complete", label: "Done" },
] as const;

const STEP_ORDER = STEPS_PIPELINE.map((s) => s.key);

function getPipelineIndex(status: string): number {
  const idx = STEP_ORDER.indexOf(status as any);
  return idx === -1 ? 0 : idx;
}

export function JobProgress({ job }: Props) {
  const isComplete = job.status === "complete";
  const isFailed = job.status === "failed";
  const logRef = useRef<HTMLDivElement>(null);
  const logs = job.log_messages ?? [];

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs.length]);
  const pipelineIdx = getPipelineIndex(job.status);

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-slate-800 truncate">
            {job.video_title || "Processing video..."}
          </p>
          {job.video_duration && (
            <p className="text-xs text-slate-500 mt-0.5">
              <Clock className="inline w-3 h-3 mr-1" />
              {formatDuration(job.video_duration)}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : isFailed ? (
            <AlertCircle className="w-4 h-4 text-red-500" />
          ) : (
            <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />
          )}
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              STATUS_COLOR[job.status] || "bg-slate-100 text-slate-600"
            }`}
          >
            {STATUS_LABELS[job.status] || job.status}
          </span>
        </div>
      </div>

      {!isFailed && (
        <>
          <Progress value={job.progress} showLabel className="mb-3" />
          <div className="flex items-center justify-between mb-3">
            {STEPS_PIPELINE.map((step, i) => {
              const done = i < pipelineIdx || isComplete;
              const active = i === pipelineIdx && !isComplete;
              return (
                <div key={step.key} className="flex flex-col items-center gap-1">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors
                      ${done ? "bg-brand-500 text-white" : active ? "bg-brand-100 text-brand-700 ring-2 ring-brand-400" : "bg-slate-100 text-slate-400"}`}
                  >
                    {done ? "✓" : i + 1}
                  </div>
                  <span className={`text-[10px] ${active ? "text-brand-600 font-medium" : "text-slate-400"}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>

          {logs.length > 0 && (
            <div
              ref={logRef}
              className="bg-slate-950 rounded-lg px-3 py-2.5 max-h-32 overflow-y-auto font-mono"
            >
              {logs.map((msg, i) => (
                <p key={i} className={`text-xs leading-relaxed ${i === logs.length - 1 && !isComplete ? "text-green-400" : "text-slate-400"}`}>
                  <span className="text-slate-600 select-none mr-1.5">›</span>
                  {msg}
                </p>
              ))}
              {!isComplete && (
                <p className="text-xs text-slate-600 animate-pulse mt-0.5 ml-4">...</p>
              )}
            </div>
          )}
        </>
      )}

      {isFailed && job.error_message && (
        <div className="mt-2 bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="text-xs text-red-700 font-medium mb-1">Error</p>
          <p className="text-xs text-red-600 font-mono whitespace-pre-wrap break-all">
            {job.error_message.slice(0, 400)}
          </p>
        </div>
      )}

      {isComplete && (
        <p className="text-xs text-green-600 mt-1">
          {job.total_steps} step{job.total_steps !== 1 ? "s" : ""} generated
        </p>
      )}
    </div>
  );
}
