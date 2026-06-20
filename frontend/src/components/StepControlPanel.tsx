import { useState } from "react";
import {
  ChevronDown, ChevronUp, RefreshCw, ImageOff, Wand2,
  Type, Zap, Code, Lightbulb, MessageSquare
} from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { useRewriteStep, useRequestDifferentImage, useSuggestCorrection } from "../hooks/useStep";
import type { Step } from "../types";

interface Props {
  jobId: string;
  step: Step;
  onCorrectionSuggested: () => void;
}

const REWRITE_OPTIONS = [
  { key: "simpler", label: "Simpler", icon: <Type className="w-3.5 h-3.5" />, desc: "Plain language, no jargon" },
  { key: "detailed", label: "More detailed", icon: <Zap className="w-3.5 h-3.5" />, desc: "Add sub-steps, explain why" },
  { key: "technical", label: "Technical", icon: <Code className="w-3.5 h-3.5" />, desc: "Precise terminology" },
  { key: "analogies", label: "With analogies", icon: <Lightbulb className="w-3.5 h-3.5" />, desc: "Everyday comparisons" },
] as const;

export function StepControlPanel({ jobId, step, onCorrectionSuggested }: Props) {
  const [open, setOpen] = useState(false);
  const [customInstr, setCustomInstr] = useState("");
  const [activeRewrite, setActiveRewrite] = useState<string | null>(null);

  const rewrite = useRewriteStep(jobId);
  const requestImage = useRequestDifferentImage(jobId);
  const suggestCorrection = useSuggestCorrection(jobId);

  const handleRewrite = (instruction: string) => {
    setActiveRewrite(instruction);
    rewrite.mutate(
      { stepId: step.id, instruction },
      { onSettled: () => setActiveRewrite(null) }
    );
  };

  const handleCustomRewrite = () => {
    if (!customInstr.trim()) return;
    handleRewrite(customInstr.trim());
    setCustomInstr("");
  };

  const handleSuggestCorrection = () => {
    suggestCorrection.mutate(step.id, {
      onSuccess: onCorrectionSuggested,
    });
  };

  return (
    <div className="border-t border-slate-100">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <Wand2 className="w-3.5 h-3.5" />
          Step controls
        </span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          {/* Rewrite options */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-2">Rewrite explanation</p>
            <div className="grid grid-cols-2 gap-1.5">
              {REWRITE_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => handleRewrite(opt.key)}
                  disabled={rewrite.isPending}
                  title={opt.desc}
                  className="flex items-center gap-1.5 px-2.5 py-2 text-xs font-medium rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {activeRewrite === opt.key && rewrite.isPending ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-500" />
                  ) : (
                    opt.icon
                  )}
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Custom instruction */}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1.5">
              <MessageSquare className="inline w-3 h-3 mr-1" />
              Custom instruction
            </p>
            <div className="flex gap-1.5">
              <Textarea
                value={customInstr}
                onChange={(e) => setCustomInstr(e.target.value)}
                placeholder="e.g. Add a warning about common mistakes..."
                rows={2}
                className="text-xs"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleCustomRewrite();
                }}
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={handleCustomRewrite}
                disabled={!customInstr.trim() || rewrite.isPending}
                loading={activeRewrite === customInstr && rewrite.isPending}
                className="self-end shrink-0"
              >
                Apply
              </Button>
            </div>
          </div>

          {/* Image + correction actions */}
          <div className="flex gap-2 pt-1 border-t border-slate-100">
            <Button
              size="sm"
              variant="outline"
              onClick={() => requestImage.mutate(step.id)}
              loading={requestImage.isPending}
              className="flex-1"
            >
              <ImageOff className="w-3.5 h-3.5" />
              Different image
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSuggestCorrection}
              loading={suggestCorrection.isPending}
              className="flex-1"
            >
              <Wand2 className="w-3.5 h-3.5" />
              AI review
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
