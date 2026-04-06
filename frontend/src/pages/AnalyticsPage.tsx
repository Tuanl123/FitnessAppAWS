import { useMemo, useState } from "react";
import { subDays, formatISO, startOfDay } from "date-fns";
import { useMetricSummary, useMetricHistory } from "../hooks/useMetrics";
import TrendChart from "../components/analytics/TrendChart";
import SummaryStats from "../components/analytics/SummaryStats";
import InsightsFeed from "../components/analytics/InsightsFeed";
import { METRIC_LABELS, type MetricType } from "../types";

const METRIC_TYPES = Object.keys(METRIC_LABELS) as MetricType[];
const RANGE_OPTIONS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<"daily" | "weekly">("daily");
  const [metricType, setMetricType] = useState<MetricType>("steps");
  const [rangeDays, setRangeDays] = useState(30);

  const startDate = formatISO(startOfDay(subDays(new Date(), rangeDays)), { representation: "date" });
  const endDate = formatISO(startOfDay(new Date()), { representation: "date" });

  const summary = useMetricSummary({ period, metric_type: metricType, start_date: startDate, end_date: endDate });
  const history = useMetricHistory({ metric_type: metricType, start_date: startDate, end_date: endDate, limit: 500 });

  const chartData = useMemo(() => {
    if (!history.data) return [];
    const points = history.data.metrics
      .map((m) => ({ date: m.recorded_at.slice(0, 10), value: m.value }))
      .reverse();
    const byDate: Record<string, number[]> = {};
    for (const p of points) {
      (byDate[p.date] ??= []).push(p.value);
    }
    return Object.entries(byDate).map(([date, vals]) => ({
      date,
      value: Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10,
    }));
  }, [history.data]);

  const aggs = summary.data?.aggregations ?? [];
  const latestAgg = aggs[0] ?? null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Analytics</h1>

      <div className="flex flex-wrap gap-3">
        <div className="flex rounded-lg bg-white shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
          {(["daily", "weekly"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-4 py-2 text-sm font-medium capitalize first:rounded-l-lg last:rounded-r-lg ${
                period === p ? "bg-teal-600 text-white" : "text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        <select
          value={metricType}
          onChange={(e) => setMetricType(e.target.value as MetricType)}
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm"
        >
          {METRIC_TYPES.map((t) => (
            <option key={t} value={t}>{METRIC_LABELS[t]}</option>
          ))}
        </select>

        <div className="flex rounded-lg bg-white shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
          {RANGE_OPTIONS.map(({ label, days }) => (
            <button
              key={days}
              onClick={() => setRangeDays(days)}
              className={`px-3 py-2 text-sm font-medium first:rounded-l-lg last:rounded-r-lg ${
                rangeDays === days ? "bg-teal-600 text-white" : "text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {history.isLoading ? (
        <div className="flex min-h-[250px] items-center justify-center rounded-xl bg-white shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800 sm:h-80">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
        </div>
      ) : (
        <TrendChart data={chartData} metricType={metricType} />
      )}

      <SummaryStats
        metricType={metricType}
        avg={latestAgg?.avg_value ?? null}
        min={latestAgg?.min_value ?? null}
        max={latestAgg?.max_value ?? null}
      />

      <InsightsFeed insights={summary.data?.insights ?? []} />
    </div>
  );
}
