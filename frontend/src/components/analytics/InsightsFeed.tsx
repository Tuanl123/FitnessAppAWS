import { useMemo } from "react";
import InsightCard from "../dashboard/InsightCard";
import type { InsightItem } from "../../types";

const GROUP_ORDER: InsightItem["type"][] = ["anomaly", "trend", "milestone"];
const GROUP_LABELS: Record<string, string> = {
  anomaly: "Alerts",
  trend: "Trends",
  milestone: "Milestones",
};

interface Props {
  insights: InsightItem[];
}

export default function InsightsFeed({ insights }: Props) {
  const grouped = useMemo(() => {
    const map: Record<string, InsightItem[]> = {};
    for (const item of insights) {
      (map[item.type] ??= []).push(item);
    }
    return GROUP_ORDER
      .filter((type) => map[type]?.length)
      .map((type) => ({ type, label: GROUP_LABELS[type] ?? type, items: map[type] }));
  }, [insights]);

  if (insights.length === 0) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Insights</h2>
        <p className="text-sm text-gray-400 dark:text-gray-500">No insights generated yet for this period.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
      <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-gray-100">Insights</h2>
      <div className="space-y-5">
        {grouped.map(({ type, label, items }) => (
          <div key={type}>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">{label}</h3>
            <div className="space-y-2">
              {items.map((item, i) => (
                <InsightCard key={`${type}-${i}`} insight={item} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
