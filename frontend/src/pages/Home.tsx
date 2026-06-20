import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { BookOpen, Youtube, Clock, ChevronRight, Trash2, AlertCircle } from "lucide-react";
import { URLInput } from "../components/URLInput";
import { ConfigPanel } from "../components/ConfigPanel";
import { Button } from "../components/ui/button";
import { useCreateJob, useJobs, useDeleteJob } from "../hooks/useJob";
import { STATUS_COLOR, STATUS_LABELS, formatDuration } from "../lib/utils";
import type { UserConfig } from "../types";

const DEFAULT_CONFIG: UserConfig = {
  experience_level: "intermediate",
  explanation_style: "detailed",
  checkpoint_frequency: "medium",
  screenshots_per_step: 2,
  user_skills: "",
};

export function Home() {
  const navigate = useNavigate();
  const [config, setConfig] = useState<UserConfig>(DEFAULT_CONFIG);
  const createJob = useCreateJob();
  const deleteJob = useDeleteJob();
  const { data: jobs = [], isLoading: jobsLoading } = useJobs();

  const handleSubmit = async (url: string, cfg: UserConfig) => {
    const job = await createJob.mutateAsync({ url, config: cfg });
    navigate(`/document/${job.id}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-brand-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-slate-900 text-sm leading-tight">YouTube to Manual</h1>
            <p className="text-xs text-slate-500">AI-powered instructional document generator</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-10">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-brand-50 text-brand-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-4 border border-brand-200">
            <Youtube className="w-3.5 h-3.5" />
            Powered by NVIDIA Nemotron
          </div>
          <h2 className="text-4xl font-bold text-slate-900 mb-3 tracking-tight">
            Turn any instructional video<br />
            <span className="text-brand-600">into a structured manual</span>
          </h2>
          <p className="text-slate-500 text-base max-w-xl mx-auto">
            Paste a YouTube URL, configure your experience level, and get an editable
            step-by-step guide with before/after images and checkpoints.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: URL Input */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <h3 className="font-semibold text-slate-800 mb-4 text-sm flex items-center gap-2">
                <Youtube className="w-4 h-4 text-red-500" />
                YouTube URL
              </h3>
              <URLInput
                onSubmit={handleSubmit}
                loading={createJob.isPending}
                defaultConfig={config}
              />
              {createJob.isError && (
                <div className="mt-3 flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3">
                  <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">
                    {createJob.error?.message || "Failed to create job"}
                  </p>
                </div>
              )}
            </div>

            {/* Recent jobs */}
            {jobs.length > 0 && (
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                <h3 className="font-semibold text-slate-800 mb-3 text-sm">Recent conversions</h3>
                <div className="space-y-2">
                  {jobs.slice(0, 8).map((job) => (
                    <div
                      key={job.id}
                      className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50 transition-colors group"
                    >
                      <button
                        onClick={() => navigate(`/document/${job.id}`)}
                        className="flex-1 flex items-center gap-3 min-w-0 text-left"
                      >
                        <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center shrink-0">
                          <Youtube className="w-4 h-4 text-red-500" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-slate-800 truncate">
                            {job.video_title || "Processing..."}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${
                                STATUS_COLOR[job.status] || "bg-slate-100 text-slate-600"
                              }`}
                            >
                              {STATUS_LABELS[job.status] || job.status}
                            </span>
                            {job.video_duration && (
                              <span className="text-xs text-slate-400 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {formatDuration(job.video_duration)}
                              </span>
                            )}
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-500 shrink-0" />
                      </button>
                      <button
                        onClick={() => deleteJob.mutate(job.id)}
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-500 transition-all"
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right: Config */}
          <div>
            <ConfigPanel config={config} onChange={setConfig} />
          </div>
        </div>

        {/* Features */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              icon: "🧠",
              title: "AI-Powered Segmentation",
              desc: "Frame difference analysis + LLM boundary validation automatically detect step boundaries.",
            },
            {
              icon: "✏️",
              title: "Per-Step Rewriting",
              desc: "Rewrite any step simpler, more detailed, or technical — without touching other steps.",
            },
            {
              icon: "✅",
              title: "Smart Checkpoints",
              desc: "Observable, specific checkpoints adapted to your experience level and frequency preference.",
            },
          ].map((f) => (
            <div key={f.title} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
              <div className="text-2xl mb-2">{f.icon}</div>
              <h4 className="font-semibold text-slate-800 text-sm mb-1">{f.title}</h4>
              <p className="text-xs text-slate-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
