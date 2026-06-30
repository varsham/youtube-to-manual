import type { Job, Step, UserConfig } from "../types";

// FastAPI now serves the built frontend itself (see backend/app/main.py), so
// frontend and API share an origin in both dev (via the Vite proxy) and prod.
// VITE_API_URL is only needed if the frontend is ever split onto its own host again.
const BACKEND = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");
const BASE = `${BACKEND}/api`;

// Frame URLs come back from the API as relative paths (/frames/…), which
// resolve correctly as long as frontend and API share an origin.
export function resolveFrameUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return BACKEND ? `${BACKEND}${url}` : url;
}

async function request<T>(
  path: string,
  opts: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Jobs
export const api = {
  jobs: {
    create: (youtube_url: string, config: UserConfig): Promise<Job> =>
      request("/jobs/", {
        method: "POST",
        body: JSON.stringify({ youtube_url, config }),
      }),

    list: (): Promise<Job[]> => request("/jobs/"),

    get: (jobId: string): Promise<Job> => request(`/jobs/${jobId}`),

    delete: (jobId: string): Promise<void> =>
      request(`/jobs/${jobId}`, { method: "DELETE" }),
  },

  steps: {
    list: (jobId: string): Promise<Step[]> =>
      request(`/jobs/${jobId}/steps/`),

    get: (jobId: string, stepId: string): Promise<Step> =>
      request(`/jobs/${jobId}/steps/${stepId}`),

    edit: (
      jobId: string,
      stepId: string,
      fields: { title?: string; explanation?: string; checkpoint?: string }
    ): Promise<Step> =>
      request(`/jobs/${jobId}/steps/${stepId}`, {
        method: "PATCH",
        body: JSON.stringify(fields),
      }),

    rewrite: (
      jobId: string,
      stepId: string,
      instruction: string
    ): Promise<Step> =>
      request(`/jobs/${jobId}/steps/${stepId}/rewrite`, {
        method: "POST",
        body: JSON.stringify({ instruction }),
      }),

    requestDifferentImage: (jobId: string, stepId: string): Promise<Step> =>
      request(`/jobs/${jobId}/steps/${stepId}/request-image`, {
        method: "POST",
      }),

    suggestCorrection: (jobId: string, stepId: string): Promise<Step> =>
      request(`/jobs/${jobId}/steps/${stepId}/suggest-correction`, {
        method: "POST",
      }),

    applyCorrection: (
      jobId: string,
      stepId: string,
      action: string,
      merge_with_step_id?: string
    ): Promise<Step[]> =>
      request(`/jobs/${jobId}/steps/${stepId}/apply-correction`, {
        method: "POST",
        body: JSON.stringify({ action, merge_with_step_id }),
      }),

    analyzeAll: (jobId: string): Promise<Step[]> =>
      request(`/jobs/${jobId}/steps/analyze-all`, { method: "POST" }),
  },

  export: {
    markdownUrl: (jobId: string) => `${BASE}/jobs/${jobId}/export/markdown`,
    pdfUrl: (jobId: string, includeCheckpoints = true) =>
      `${BASE}/jobs/${jobId}/export/pdf${includeCheckpoints ? "" : "?include_checkpoints=false"}`,
  },
};
