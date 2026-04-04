import { format } from "date-fns";
import type { InsightItem } from "../../types";

const TYPE_STYLES: Record<string, { border: string; bg: string; label: string; icon: string }> = {
  anomaly: { border: "border-red-300 dark:border-red-700", bg: "bg-red-50 dark:bg-red-950", label: "Alert", icon: "⚠" },
  milestone: { border: "border-amber-300 dark:border-amber-700", bg: "bg-amber-50 dark:bg-amber-950", label: "Milestone", icon: "🏆" },
  trend: { border: "border-teal-300 dark:border-teal-700", bg: "bg-teal-50 dark:bg-teal-950", label: "Trend", icon: "📈" },
};

function cleanDescription(desc: string): string {
  return desc.replace(/^\[\d{4}-\d{2}-\d{2}\]\s*/, "");
}

interface Props {
  insight: InsightItem;
}

export default function InsightCard({ insight }: Props) {
  const style = TYPE_STYLES[insight.type] ?? TYPE_STYLES.trend;

  return (
    <div className={`rounded-lg border-l-4 ${style.border} ${style.bg} p-4`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {style.icon} {style.label}
        </span>
        <span className="text-xs text-gray-400 dark:text-gray-500">{format(new Date(insight.generated_at), "MMM d")}</span>
      </div>
      <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{cleanDescription(insight.description)}</p>
    </div>
  );
}
