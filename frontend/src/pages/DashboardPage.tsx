import { Link } from "react-router-dom";
import { subDays, formatISO, startOfDay } from "date-fns";
import { useMetricHistory, useMetricSummary } from "../hooks/useMetrics";
import MetricCard from "../components/dashboard/MetricCard";
import RecentActivity from "../components/dashboard/RecentActivity";
import InsightCard from "../components/dashboard/InsightCard";
import type { MetricType } from "../types";

const DASHBOARD_METRICS: MetricType[] = [
  "heart_rate",
  "steps",
  "workout_duration",
  "calories_burned",
  "sleep_hours",
];

export default function DashboardPage() {
  const today = formatISO(startOfDay(new Date()), { representation: "date" });
  const weekAgo = formatISO(startOfDay(subDays(new Date(), 7)), { representation: "date" });

  const history = useMetricHistory({ limit: 10, start_date: weekAgo });
  const summary = useMetricSummary({ period: "daily", start_date: weekAgo, end_date: today });

  const latestByType: Partial<Record<MetricType, number>> = {};
  if (history.data) {
    for (const item of history.data.metrics) {
      const mt = item.metric_type as MetricType;
      if (!(mt in latestByType)) latestByType[mt] = item.value;
    }
  }

  const insights = summary.data?.insights?.slice(0, 3) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Dashboard</h1>
        <Link
          to="/log"
          className="self-start rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
        >
          Log Metric
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {DASHBOARD_METRICS.map((mt) => (
          <MetricCard key={mt} metricType={mt} value={latestByType[mt] ?? null} />
        ))}
      </div>

      <RecentActivity items={history.data?.metrics ?? []} loading={history.isLoading} />

      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Latest Insights</h2>
        {insights.length > 0 ? (
          <div className="space-y-3">
            {insights.map((ins, i) => (
              <InsightCard key={i} insight={ins} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 dark:text-gray-500">
            Trends, milestones, and alerts will appear here once you have enough data.
          </p>
        )}
      </div>
    </div>
  );
}
