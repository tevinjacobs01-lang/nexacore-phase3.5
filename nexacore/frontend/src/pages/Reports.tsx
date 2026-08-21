import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const REPORT_TYPES = [
  { key: "daily-lead", label: "Daily Lead Report" },
  { key: "weekly-performance", label: "Weekly Performance" },
  { key: "monthly-imports", label: "Monthly Listings Imported" },
  { key: "contact-conversion", label: "Contact Conversion" },
  { key: "score-breakdown", label: "Lead Score Breakdown" },
];

export default function Reports() {
  const [selected, setSelected] = useState(REPORT_TYPES[0].key);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .get(`/reports/${selected}`)
      .then((res) => setRows(res.data))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [selected]);

  async function handleExport(format: "csv" | "xlsx" | "pdf") {
    const res = await api.get(`/reports/${selected}/export`, {
      params: { format },
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${selected}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Reports</h2>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {REPORT_TYPES.map((r) => (
            <button
              key={r.key}
              onClick={() => setSelected(r.key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                selected === r.key
                  ? "bg-brand-600 text-white"
                  : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>

        <div className="flex gap-2">
          {(["csv", "xlsx", "pdf"] as const).map((format) => (
            <button
              key={format}
              onClick={() => handleExport(format)}
              className="rounded-md border border-gray-300 dark:border-gray-700 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Export {format.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
            <tr>
              {columns.map((col) => (
                <th key={col} className="px-4 py-2 text-left">
                  {col.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {rows.map((row, i) => (
              <tr key={i} className="bg-white dark:bg-gray-950">
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2">
                    {String(row[col] ?? "–")}
                  </td>
                ))}
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={Math.max(columns.length, 1)} className="px-4 py-6 text-center text-gray-400">
                  No data for this report yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
