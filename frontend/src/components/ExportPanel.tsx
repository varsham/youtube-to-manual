import { useState } from "react";
import { FileText, FileDown, Wand2 } from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardHeader, CardContent } from "./ui/card";
import { useAnalyzeAllSteps } from "../hooks/useStep";
import { api } from "../lib/api";
import type { Job } from "../types";

interface Props {
  job: Job;
}

export function ExportPanel({ job }: Props) {
  const analyzeAll = useAnalyzeAllSteps(job.id);
  const [includeCheckpoints, setIncludeCheckpoints] = useState(true);

  const handleDownload = (url: string, filename: string) => {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
  };

  const safeTitle = (job.video_title || "manual")
    .replace(/[^a-z0-9\s-]/gi, "")
    .trim()
    .replace(/\s+/g, "-")
    .toLowerCase();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileDown className="w-4 h-4 text-slate-500" />
          <h3 className="font-semibold text-slate-800 text-sm">Export</h3>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          onClick={() => handleDownload(api.export.markdownUrl(job.id), `${safeTitle}.md`)}
        >
          <FileText className="w-3.5 h-3.5" />
          Download Markdown
        </Button>
        <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={includeCheckpoints}
            onChange={(e) => setIncludeCheckpoints(e.target.checked)}
            className="rounded"
          />
          Include checkpoints
        </label>
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start"
          onClick={() => handleDownload(api.export.pdfUrl(job.id, includeCheckpoints), `${safeTitle}.pdf`)}
        >
          <FileDown className="w-3.5 h-3.5" />
          Download PDF
        </Button>

        <div className="border-t border-slate-100 pt-2 mt-1">
          <Button
            variant="secondary"
            size="sm"
            className="w-full justify-start"
            onClick={() => analyzeAll.mutate()}
            loading={analyzeAll.isPending}
          >
            <Wand2 className="w-3.5 h-3.5" />
            AI review all steps
          </Button>
          <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
            Analyzes all steps for quality issues and suggests corrections.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
