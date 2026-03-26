export interface User {
  user_id: string;
  email: string;
  name: string;
  age: number | null;
  weight: number | null;
  fitness_goals: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse extends AuthTokens {
  user_id: string;
  email: string;
  name: string;
}

export type MetricType =
  | "heart_rate"
  | "steps"
  | "workout_duration"
  | "calories_burned"
  | "sleep_hours"
  | "distance_km";

export interface MetricIngest {
  metric_type: MetricType;
  value: number;
  recorded_at: string;
}

export interface MetricHistoryItem {
  id: string;
  metric_type: string;
  value: number;
  recorded_at: string;
}

export interface MetricHistoryResponse {
  metrics: MetricHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AggregationItem {
  metric_type: string;
  period: string;
  date: string;
  avg_value: number;
  min_value: number;
  max_value: number;
}

export interface InsightItem {
  type: "anomaly" | "trend" | "milestone";
  description: string;
  generated_at: string;
}

export interface MetricSummaryResponse {
  aggregations: AggregationItem[];
  insights: InsightItem[];
}

export const METRIC_LABELS: Record<MetricType, string> = {
  heart_rate: "Heart Rate",
  steps: "Steps",
  workout_duration: "Workout Duration",
  calories_burned: "Calories Burned",
  sleep_hours: "Sleep",
  distance_km: "Distance",
};

export const METRIC_UNITS: Record<MetricType, string> = {
  heart_rate: "bpm",
  steps: "steps",
  workout_duration: "min",
  calories_burned: "kcal",
  sleep_hours: "hrs",
  distance_km: "km",
};
