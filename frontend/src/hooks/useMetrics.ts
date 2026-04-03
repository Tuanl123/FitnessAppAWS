import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as metricsApi from "../api/metrics";
import type { MetricIngest } from "../types";

export function useMetricHistory(params: {
  metric_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ["metricHistory", params],
    queryFn: () => metricsApi.getHistory(params),
    staleTime: 30_000,
  });
}

export function useMetricSummary(params: {
  period: "daily" | "weekly";
  metric_type?: string;
  start_date?: string;
  end_date?: string;
}) {
  return useQuery({
    queryKey: ["metricSummary", params],
    queryFn: () => metricsApi.getSummary(params),
    staleTime: 60_000,
  });
}

export function useIngestMetric() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (metric: MetricIngest) => metricsApi.ingestMetric(metric),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["metricHistory"] });
      queryClient.invalidateQueries({ queryKey: ["metricSummary"] });
    },
  });
}

export function useIngestBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (metrics: MetricIngest[]) => metricsApi.ingestBatch(metrics),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["metricHistory"] });
      queryClient.invalidateQueries({ queryKey: ["metricSummary"] });
    },
  });
}
