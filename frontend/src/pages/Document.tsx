import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, BookOpen, RefreshCw, Youtube, AlertCircle } from "lucide-react";
import { useJob } from "../hooks/useJob";
import { useSteps } from "../hooks/useStep";
import { JobProgress } from "../components/JobProgress";
import { StepCard } from "../components/StepCard";
import { ConfigPanel } from "../components/ConfigPanel";
import { ExportPanel } from "../components/ExportPanel";
import { Button } from "../components/ui/button";
import { formatDuration } from "../lib/utils";
import type { UserConfig } from "../types";

export function Document() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const { data: job, isLoading: jobLoading, isError: jobError, refetch: refetchJob } = useJob(jobId ?? null);
  const { data: steps = [], isLoading: stepsLoading } = useSteps(
    job?.status === "complete" ? jobId ?? null : null
  );

  if (jobLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-brand-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (jobError || !job) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-slate-700 mb-4">Job not found</p>
          <Button onClick={() => navigate("/")} variant="secondary" size="sm">
            <ArrowLeft className="w-3.5 h-3.5" />
            Go home
          </Button>
        </div>
      </div>
    );
  }

  const isProcessing = job.status !== "complete" && job.status !== "failed";
  const isComplete = job.status === "complete";

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate("/")}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center shrink-0">
            <BookOpen className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-slate-900 text-sm truncate">
              {job.video_title || "Processing..."}
            </h1>
            {job.video_duration && (
              <p className="text-xs text-slate-500">
                {formatDuration(job.video_duration)} video
                {isComplete && steps.length > 0 && ` · ${steps.length} steps`}
              </p>
            )}
          </div>
          {job.video_thumbnail && (
            <a
              href={job.youtube_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-600 transition-colors"
            >
              <Youtube className="w-3.5 h-3.5" />
              Source
            </a>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 flex gap-6">
        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Progress card */}
          {(isProcessing || job.status === "failed") && (
            <JobProgress job={job} />
          )}

          {/* Steps */}
          {isComplete && (
            <>
              {stepsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="text-center">
                    <RefreshCw className="w-6 h-6 text-brand-400 animate-spin mx-auto mb-2" />
                    <p className="text-sm text-slate-500">Loading steps...</p>
                  </div>
                </div>
              ) : steps.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
                  <AlertCircle className="w-8 h-8 text-amber-400 mx-auto mb-3" />
                  <p className="text-slate-600 text-sm">No steps generated. The video may not have had detectable procedural content.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="font-semibold text-slate-700 text-sm">
                      {steps.length} Steps
                    </h2>
                    <p className="text-xs text-slate-400">
                      {job.config?.experience_level} · {job.config?.explanation_style}
                    </p>
                  </div>
                  {steps.map((step, i) => (
                    <StepCard
                      key={step.id}
                      jobId={job.id}
                      step={step}
                      allSteps={steps}
                      index={i}
                      youtubeUrl={job.youtube_url}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {/* Waiting state */}
          {isProcessing && (
            <div className="bg-white border border-slate-200 rounded-xl p-8 text-center">
              <div className="w-12 h-12 bg-brand-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <RefreshCw className="w-5 h-5 text-brand-500 animate-spin" />
              </div>
              <p className="text-slate-600 font-medium text-sm mb-1">
                Generating your manual...
              </p>
              <p className="text-xs text-slate-400">
                Steps will appear here when processing is complete.
              </p>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="w-72 shrink-0 space-y-4 sticky top-[61px] self-start max-h-[calc(100vh-80px)] overflow-y-auto">
          {isComplete && <ExportPanel job={job} />}
          <ConfigPanel
            config={job.config as UserConfig}
            onChange={() => {}}
            disabled
          />
          <div className="bg-slate-100 rounded-xl p-3 text-xs text-slate-500 leading-relaxed">
            <p className="font-semibold text-slate-600 mb-1">Tip</p>
            Use "AI review" on individual steps or "AI review all steps" to detect segmentation issues.
            All AI changes require your explicit approval.
          </div>
        </div>
      </div>
    </div>
  );
}
