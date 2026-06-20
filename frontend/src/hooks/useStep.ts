import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export function useSteps(jobId: string | null) {
  return useQuery({
    queryKey: ["steps", jobId],
    queryFn: () => api.steps.list(jobId!),
    enabled: !!jobId,
    staleTime: 30_000,
  });
}

export function useEditStep(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      stepId,
      fields,
    }: {
      stepId: string;
      fields: { title?: string; explanation?: string; checkpoint?: string };
    }) => api.steps.edit(jobId, stepId, fields),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steps", jobId] });
    },
  });
}

export function useRewriteStep(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stepId, instruction }: { stepId: string; instruction: string }) =>
      api.steps.rewrite(jobId, stepId, instruction),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steps", jobId] });
    },
  });
}

export function useRequestDifferentImage(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) => api.steps.requestDifferentImage(jobId, stepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steps", jobId] });
    },
  });
}

export function useSuggestCorrection(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (stepId: string) => api.steps.suggestCorrection(jobId, stepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steps", jobId] });
    },
  });
}

export function useApplyCorrection(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      stepId,
      action,
      mergeWithStepId,
    }: {
      stepId: string;
      action: string;
      mergeWithStepId?: string;
    }) => api.steps.applyCorrection(jobId, stepId, action, mergeWithStepId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steps", jobId] });
    },
  });
}

export function useAnalyzeAllSteps(jobId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.steps.analyzeAll(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["steps", jobId] });
    },
  });
}
