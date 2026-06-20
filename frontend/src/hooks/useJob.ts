import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { UserConfig } from "../types";

const POLL_INTERVAL = 2500;

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: api.jobs.list,
    staleTime: 10_000,
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.jobs.get(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return POLL_INTERVAL;
      if (status === "complete" || status === "failed") return false;
      return POLL_INTERVAL;
    },
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ url, config }: { url: string; config: UserConfig }) =>
      api.jobs.create(url, config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => api.jobs.delete(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
