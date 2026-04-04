import { format } from "date-fns";
import { METRIC_LABELS, METRIC_UNITS, type MetricHistoryItem, type MetricType } from "../../types";

interface Props {
  items: MetricHistoryItem[];
  loading?: boolean;
}

export default function RecentActivity({ items, loading }: Props) {
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Recent Activity</h2>

      {loading ? (
        <div className="flex justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-600 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-400 dark:text-gray-500">No metrics logged yet.</p>
      ) : (
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {items.map((item) => {
            const mt = item.metric_type as MetricType;
            return (
              <div key={item.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {METRIC_LABELS[mt] ?? item.metric_type}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    {format(new Date(item.recorded_at), "MMM d, yyyy h:mm a")}
                  </p>
                </div>
                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {item.value} <span className="text-xs font-normal text-gray-400 dark:text-gray-500">{METRIC_UNITS[mt] ?? ""}</span>
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
