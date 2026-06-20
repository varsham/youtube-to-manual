import { useState } from "react";
import {
  CheckCircle2, AlertTriangle, Clock, ChevronRight, Eye
} from "lucide-react";
import { Badge } from "./ui/badge";
import { EditableField } from "./EditableField";
import { StepControlPanel } from "./StepControlPanel";
import { CorrectionModal } from "./CorrectionModal";
import { useEditStep } from "../hooks/useStep";
import { formatTimestamp, youtubeAtTime } from "../lib/utils";
import type { Step } from "../types";

interface Props {
  jobId: string;
  step: Step;
  allSteps: Step[];
  index: number;
  youtubeUrl?: string;
}

function FrameImage({ url, label }: { url: string | null; label: string }) {
  const [err, setErr] = useState(false);

  if (!url || err) {
    return (
      <div className="w-full aspect-video bg-slate-100 rounded-lg flex items-center justify-center border border-slate-200">
        <div className="text-center">
          <Eye className="w-5 h-5 text-slate-300 mx-auto mb-1" />
          <p className="text-xs text-slate-400">{label}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative group">
      <img
        src={url}
        alt={label}
        onError={() => setErr(true)}
        className="w-full aspect-video object-cover rounded-lg border border-slate-200 bg-slate-100"
        loading="lazy"
      />
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/50 to-transparent rounded-b-lg px-2 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <span className="text-white text-xs font-medium">{label}</span>
      </div>
    </div>
  );
}

const CORRECTION_BADGE: Record<string, { label: string; variant: "warning" | "info" | "success" | "default" }> = {
  suggested: { label: "AI suggestion", variant: "warning" },
  approved: { label: "Corrected", variant: "success" },
  rejected: { label: "Reviewed", variant: "default" },
};

export function StepCard({ jobId, step, allSteps, index, youtubeUrl }: Props) {
  const [showCorrection, setShowCorrection] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const editStep = useEditStep(jobId);

  const hasCorrectionSuggestion = step.correction_status === "suggested" && step.correction_suggestion;
  const corrBadge = CORRECTION_BADGE[step.correction_status];

  const adjacentSteps = allSteps.filter(
    (s) => s.id !== step.id && Math.abs(s.order - step.order) <= 1
  );

  const duration =
    step.segment_start != null && step.segment_end != null
      ? step.segment_end - step.segment_start
      : null;

  return (
    <>
      <div
        className={`bg-white rounded-xl border shadow-sm transition-all overflow-hidden
          ${hasCorrectionSuggestion ? "border-amber-300 shadow-amber-100" : "border-slate-200"}`}
      >
        {/* Step header */}
        <div
          className="flex items-start gap-3 px-4 py-3.5 cursor-pointer select-none hover:bg-slate-50/50 transition-colors"
          onClick={() => setCollapsed((c) => !c)}
        >
          {/* Step number */}
          <div className="shrink-0 w-7 h-7 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center mt-0.5">
            {index + 1}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <EditableField
                value={step.title}
                onSave={(v) => editStep.mutateAsync({ stepId: step.id, fields: { title: v } })}
                displayClassName="font-semibold text-slate-800 text-sm"
              />
              {corrBadge && (
                <Badge variant={corrBadge.variant}>{corrBadge.label}</Badge>
              )}
            </div>
            {duration != null && (
              <p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1 flex-wrap">
                <Clock className="w-3 h-3" />
                {youtubeUrl ? (
                  <>
                    <a
                      href={youtubeAtTime(youtubeUrl, step.segment_start!)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="hover:text-brand-600 hover:underline transition-colors"
                      title={`Open YouTube at ${formatTimestamp(step.segment_start!)}`}
                    >
                      {formatTimestamp(step.segment_start!)}–{formatTimestamp(step.segment_end!)}
                    </a>
                    <span className="text-slate-300">({Math.round(duration)}s)</span>
                  </>
                ) : (
                  <>
                    {formatTimestamp(step.segment_start!)}–{formatTimestamp(step.segment_end!)}
                    <span className="ml-1 text-slate-300">({Math.round(duration)}s)</span>
                  </>
                )}
              </p>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {hasCorrectionSuggestion && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowCorrection(true);
                }}
                className="flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded-lg hover:bg-amber-100 transition-colors"
              >
                <AlertTriangle className="w-3 h-3" />
                Review
              </button>
            )}
            <ChevronRight
              className={`w-4 h-4 text-slate-400 transition-transform ${collapsed ? "" : "rotate-90"}`}
            />
          </div>
        </div>

        {/* Step body */}
        {!collapsed && (
          <>
            {/* Before / After images */}
            {(step.before_frame_url || step.after_frame_url) && (
              <div className="px-4 pb-3 grid grid-cols-2 gap-3">
                <FrameImage url={step.before_frame_url} label="Before" />
                <FrameImage url={step.after_frame_url} label="After" />
              </div>
            )}

            {/* Explanation */}
            <div className="px-4 pb-3">
              <EditableField
                value={step.explanation}
                onSave={(v) => editStep.mutateAsync({ stepId: step.id, fields: { explanation: v } })}
                multiline
                displayClassName="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap"
              />
            </div>

            {/* Checkpoint */}
            {step.checkpoint && (
              <div className="mx-4 mb-3 bg-green-50 border border-green-200 rounded-lg px-3 py-2.5">
                <div className="flex items-center gap-1.5 mb-1">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                  <span className="text-xs font-semibold text-green-700 uppercase tracking-wide">Checkpoint</span>
                </div>
                <EditableField
                  value={step.checkpoint}
                  onSave={(v) => editStep.mutateAsync({ stepId: step.id, fields: { checkpoint: v } })}
                  multiline
                  displayClassName="text-sm text-green-800"
                />
              </div>
            )}

            {/* Controls */}
            <StepControlPanel
              jobId={jobId}
              step={step}
              onCorrectionSuggested={() => setShowCorrection(true)}
            />
          </>
        )}
      </div>

      {showCorrection && step.correction_suggestion && (
        <CorrectionModal
          jobId={jobId}
          step={step}
          adjacentSteps={adjacentSteps}
          onClose={() => setShowCorrection(false)}
        />
      )}
    </>
  );
}
