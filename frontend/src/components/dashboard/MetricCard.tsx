import type { MetricType } from "../../types";
import { METRIC_LABELS, METRIC_UNITS } from "../../types";

const ICONS: Record<MetricType, string> = {
  heart_rate: "M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z",
  steps: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
  workout_duration: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  calories_burned: "M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z",
  sleep_hours: "M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z",
  distance_km: "M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7",
};

interface Props {
  metricType: MetricType;
  value: number | null;
  previousValue?: number | null;
}

export default function MetricCard({ metricType, value, previousValue }: Props) {
  const label = METRIC_LABELS[metricType];
  const unit = METRIC_UNITS[metricType];
  const icon = ICONS[metricType];

  let trend: { pct: number; direction: "up" | "down" } | null = null;
  if (value != null && previousValue != null && previousValue !== 0) {
    const pct = ((value - previousValue) / previousValue) * 100;
    trend = { pct: Math.abs(pct), direction: pct >= 0 ? "up" : "down" };
  }

  return (
    <div className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
      <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d={icon} />
        </svg>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value != null ? `${Number(value.toFixed(1))}` : "\u2014"}
        {value != null && <span className="ml-1 text-sm font-normal text-gray-400 dark:text-gray-500">{unit}</span>}
      </p>
      {trend ? (
        <p className={`mt-1 text-xs font-medium ${trend.direction === "up" ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"}`}>
          {trend.direction === "up" ? "\u2191" : "\u2193"} {trend.pct.toFixed(1)}% vs prior
        </p>
      ) : (
        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{value != null ? "Latest value" : "No data yet"}</p>
      )}
    </div>
  );
}
