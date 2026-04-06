import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { METRIC_LABELS, METRIC_UNITS, type MetricType } from "../../types";

interface DataPoint {
  date: string;
  value: number;
}

interface Props {
  data: DataPoint[];
  metricType: MetricType;
}

function getChartColors() {
  const s = getComputedStyle(document.documentElement);
  return {
    stroke: s.getPropertyValue("--chart-stroke").trim(),
    fillStart: s.getPropertyValue("--chart-fill-start").trim(),
    fillEnd: s.getPropertyValue("--chart-fill-end").trim(),
    grid: s.getPropertyValue("--chart-grid").trim(),
    axis: s.getPropertyValue("--chart-axis").trim(),
    tooltipBg: s.getPropertyValue("--chart-tooltip-bg").trim(),
    tooltipBorder: s.getPropertyValue("--chart-tooltip-border").trim(),
    tooltipText: s.getPropertyValue("--chart-tooltip-text").trim(),
  };
}

export default function TrendChart({ data, metricType }: Props) {
  const unit = METRIC_UNITS[metricType];
  const label = METRIC_LABELS[metricType];
  const c = getChartColors();

  if (data.length === 0) {
    return (
      <div className="flex min-h-[250px] items-center justify-center rounded-xl bg-white shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800 sm:h-80">
        <p className="text-sm text-gray-400 dark:text-gray-500">No data available for {label}.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
      <h3 className="mb-2 text-sm font-medium text-gray-500 dark:text-gray-400">{label} over time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={c.stroke} stopOpacity={0.15} />
              <stop offset="95%" stopColor={c.stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
          <XAxis dataKey="date" tick={{ fontSize: 12, fill: c.axis }} stroke={c.axis} />
          <YAxis tick={{ fontSize: 12, fill: c.axis }} stroke={c.axis} unit={` ${unit}`} />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: `1px solid ${c.tooltipBorder}`,
              fontSize: 13,
              backgroundColor: c.tooltipBg,
              color: c.tooltipText,
            }}
            formatter={(v) => [`${v} ${unit}`, label]}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={c.stroke}
            strokeWidth={2}
            fill="url(#colorValue)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
