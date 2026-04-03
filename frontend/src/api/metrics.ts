import apiClient from "./client";
import type {
  MetricIngest,
  MetricHistoryResponse,
  MetricSummaryResponse,
} from "../types";

export async function ingestMetric(
  metric: MetricIngest,
): Promise<{ message: string; message_id: string }> {
  const { data } = await apiClient.post("/api/metrics/ingest", metric);
  return data;
}

export async function ingestBatch(
  metrics: MetricIngest[],
): Promise<{ message: string; accepted_count: number; message_ids: string[] }> {
  const { data } = await apiClient.post("/api/metrics/ingest/batch", {
    metrics,
  });
  return data;
}

export async function getHistory(params: {
  metric_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<MetricHistoryResponse> {
  const { data } = await apiClient.get("/api/metrics/history", { params });
  return data;
}

export async function getSummary(params: {
  period: "daily" | "weekly";
  metric_type?: string;
  start_date?: string;
  end_date?: string;
}): Promise<MetricSummaryResponse> {
  const { data } = await apiClient.get("/api/metrics/summary", { params });
  return data;
}
