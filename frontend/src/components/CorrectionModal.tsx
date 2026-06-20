import { useState } from "react";
import { AlertTriangle, CheckCircle, XCircle, GitMerge, Scissors, RefreshCw, X } from "lucide-react";
import { Button } from "./ui/button";
import { useApplyCorrection } from "../hooks/useStep";
import type { Step, CorrectionSuggestion } from "../types";

interface Props {
  jobId: string;
  step: Step;
  adjacentSteps: Step[];
  onClose: () => void;
}

const ISSUE_ICON: Record<string, React.ReactNode> = {
  too_broad: <Scissors className="w-4 h-4 text-amber-500" />,
  too_narrow: <GitMerge className="w-4 h-4 text-blue-500" />,
  unclear_boundary: <AlertTriangle className="w-4 h-4 text-amber-500" />,
  explanation_quality: <RefreshCw className="w-4 h-4 text-violet-500" />,
};

const ACTION_MAP: Record<string, string> = {
  split: "approve_split",
  merge: "approve_merge",
  rewrite: "approve_rewrite",
};

export function CorrectionModal({ jobId, step, adjacentSteps, onClose }: Props) {
  const suggestion = step.correction_suggestion as CorrectionSuggestion;
  const apply = useApplyCorrection(jobId);
  const [selectedMergeId, setSelectedMergeId] = useState<string>(
    adjacentSteps[0]?.id || ""
  );

  const proposedAction = suggestion?.proposed_action || "";
  const hasIssue = suggestion && !suggestion.message;

  const handleApply = () => {
    const action = ACTION_MAP[proposedAction] || "reject";
    apply.mutate(
      { stepId: step.id, action, mergeWithStepId: action === "approve_merge" ? selectedMergeId : undefined },
      { onSuccess: onClose }
    );
  };

  const handleReject = () => {
    apply.mutate({ stepId: step.id, action: "reject" }, { onSuccess: onClose });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            AI Correction Suggestion
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Step reference */}
          <div className="bg-slate-50 rounded-lg px-3 py-2">
            <p className="text-xs text-slate-500 mb-0.5">Step {step.order + 1}</p>
            <p className="text-sm font-medium text-slate-800">{step.title}</p>
          </div>

          {hasIssue ? (
            <>
              {/* Issue type */}
              <div className="flex items-center gap-2">
                {ISSUE_ICON[suggestion.issue_type || ""] || <AlertTriangle className="w-4 h-4 text-slate-400" />}
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  {(suggestion.issue_type || "").replace(/_/g, " ")}
                </span>
              </div>

              {/* Description */}
              <p className="text-sm text-slate-700">{suggestion.description}</p>

              {/* Proposed fix */}
              {suggestion.proposed_detail && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
                  <p className="text-xs font-medium text-blue-700 mb-1">Proposed fix</p>
                  <p className="text-sm text-blue-800">{suggestion.proposed_detail}</p>
                </div>
              )}

              {/* Merge target selector */}
              {proposedAction === "merge" && adjacentSteps.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">
                    Merge with step:
                  </label>
                  <select
                    value={selectedMergeId}
                    onChange={(e) => setSelectedMergeId(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2"
                  >
                    {adjacentSteps.map((s) => (
                      <option key={s.id} value={s.id}>
                        Step {s.order + 1}: {s.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle className="w-4 h-4" />
              <p className="text-sm">{suggestion?.message || "No issues detected."}</p>
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-slate-100 flex gap-2 justify-end">
          <Button variant="ghost" size="sm" onClick={handleReject} disabled={apply.isPending}>
            <XCircle className="w-3.5 h-3.5" />
            Keep unchanged
          </Button>
          {hasIssue && (
            <Button
              size="sm"
              onClick={handleApply}
              loading={apply.isPending}
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Apply fix
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
