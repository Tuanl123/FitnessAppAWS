import { METRIC_UNITS, type MetricType } from "../../types";

interface Props {
  metricType: MetricType;
  avg: number | null;
  min: number | null;
  max: number | null;
  count?: number;
}

export default function SummaryStats({ metricType, avg, min, max }: Props) {
  const unit = METRIC_UNITS[metricType];

  const cards = [
    { label: "Average", value: avg },
    { label: "Minimum", value: min },
    { label: "Maximum", value: max },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {cards.map(({ label, value }) => (
        <div key={label} className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
            {value != null ? value.toFixed(1) : "\u2014"}
            {value != null && <span className="ml-1 text-sm font-normal text-gray-400 dark:text-gray-500">{unit}</span>}
          </p>
        </div>
      ))}
    </div>
  );
}
