import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import axios from "axios";
import { useIngestMetric, useIngestBatch } from "../hooks/useMetrics";
import { METRIC_LABELS, METRIC_UNITS, type MetricType, type MetricIngest } from "../types";

const METRIC_TYPES = Object.keys(METRIC_LABELS) as MetricType[];
const INPUT_CLS = "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm";

function extractErrorMessage(error: unknown, fallback: string): string {
  if (!axios.isAxiosError(error) || !error.response?.data) return fallback;
  const data = error.response.data;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((d: { loc?: string[]; msg?: string }) => {
        const field = d.loc?.slice(-1)[0] ?? "field";
        return `${field}: ${d.msg}`;
      })
      .join("\n");
  }
  if (typeof data.detail === "string") return data.detail;
  return fallback;
}

export default function LogMetricPage() {
  const [batchMode, setBatchMode] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Log a Metric</h1>
        <button
          onClick={() => setBatchMode((b) => !b)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          {batchMode ? "Single Mode" : "Batch Mode"}
        </button>
      </div>

      {batchMode ? <BatchForm /> : <SingleForm />}
    </div>
  );
}

function SingleForm() {
  const ingest = useIngestMetric();
  const [metricType, setMetricType] = useState<MetricType>("steps");
  const [value, setValue] = useState("");
  const [recordedAt, setRecordedAt] = useState(new Date().toISOString().slice(0, 16));
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await ingest.mutateAsync({
        metric_type: metricType,
        value: parseFloat(value),
        recorded_at: new Date(recordedAt).toISOString(),
      });
      toast.success("Metric logged!");
      setSubmitted(true);
      setValue("");
    } catch (err) {
      toast.error(extractErrorMessage(err, "Failed to log metric."), { duration: 6000 });
    }
  }

  if (submitted) {
    return (
      <div className="w-full max-w-lg rounded-xl bg-white p-6 text-center shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
        <p className="mb-4 text-lg font-medium text-gray-800 dark:text-gray-200">Metric accepted for processing!</p>
        <div className="flex justify-center gap-3">
          <button
            onClick={() => setSubmitted(false)}
            className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
          >
            Log Another
          </button>
          <Link
            to="/"
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            View Dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Metric Type</label>
          <select value={metricType} onChange={(e) => setMetricType(e.target.value as MetricType)} className={INPUT_CLS}>
            {METRIC_TYPES.map((t) => (
              <option key={t} value={t}>{METRIC_LABELS[t]}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Value ({METRIC_UNITS[metricType]})
          </label>
          <input type="number" required step="any" min="0" value={value} onChange={(e) => setValue(e.target.value)} className={INPUT_CLS} placeholder="0" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Recorded At</label>
          <input type="datetime-local" value={recordedAt} onChange={(e) => setRecordedAt(e.target.value)} className={INPUT_CLS} />
        </div>
        <button type="submit" disabled={ingest.isPending} className="w-full rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
          {ingest.isPending ? "Submitting..." : "Submit Metric"}
        </button>
      </form>
    </div>
  );
}

interface BatchRow {
  id: string;
  metric_type: MetricType;
  value: string;
  recorded_at: string;
}

function BatchForm() {
  const batch = useIngestBatch();
  const now = new Date().toISOString().slice(0, 16);
  const [rows, setRows] = useState<BatchRow[]>([
    { id: crypto.randomUUID(), metric_type: "steps", value: "", recorded_at: now },
  ]);

  function addRow() {
    if (rows.length >= 50) return;
    setRows([...rows, { id: crypto.randomUUID(), metric_type: "steps", value: "", recorded_at: now }]);
  }

  function removeRow(id: string) {
    if (rows.length <= 1) return;
    setRows(rows.filter((r) => r.id !== id));
  }

  function updateRow(id: string, field: keyof BatchRow, val: string) {
    setRows(rows.map((r) => (r.id === id ? { ...r, [field]: val } : r)));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const metrics: MetricIngest[] = rows.map((r) => ({
      metric_type: r.metric_type,
      value: parseFloat(r.value),
      recorded_at: new Date(r.recorded_at).toISOString(),
    }));

    try {
      const res = await batch.mutateAsync(metrics);
      toast.success(`${res.accepted_count} metrics logged!`);
      setRows([{ id: crypto.randomUUID(), metric_type: "steps", value: "", recorded_at: now }]);
    } catch (err) {
      toast.error(extractErrorMessage(err, "Batch submission failed."), { duration: 6000 });
    }
  }

  const rowInputCls = "rounded-lg border border-gray-300 bg-white px-2 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm";

  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-3">
          {rows.map((row) => (
            <div key={row.id} className="grid grid-cols-1 items-end gap-2 sm:grid-cols-[auto_7rem_auto_auto]">
              <select value={row.metric_type} onChange={(e) => updateRow(row.id, "metric_type", e.target.value)} className={rowInputCls}>
                {METRIC_TYPES.map((t) => (
                  <option key={t} value={t}>{METRIC_LABELS[t]}</option>
                ))}
              </select>
              <input type="number" required step="any" min="0" placeholder="Value" value={row.value} onChange={(e) => updateRow(row.id, "value", e.target.value)} className={rowInputCls} />
              <input type="datetime-local" value={row.recorded_at} onChange={(e) => updateRow(row.id, "recorded_at", e.target.value)} className={rowInputCls} />
              <button type="button" onClick={() => removeRow(row.id)} className="rounded-lg p-2 text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button type="button" onClick={addRow} disabled={rows.length >= 50} className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800">
            + Add Row
          </button>
          <button type="submit" disabled={batch.isPending} className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
            {batch.isPending ? "Submitting..." : `Submit ${rows.length} Metric${rows.length > 1 ? "s" : ""}`}
          </button>
        </div>
      </form>
    </div>
  );
}
