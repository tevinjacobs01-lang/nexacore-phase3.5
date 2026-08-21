import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Source, ScanJob } from "@/types/collection";

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    running: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    pending: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    cancelled: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] ?? colors.pending}`}>
      {status}
    </span>
  );
}

export default function Collection() {
  const [sources, setSources] = useState<Source[]>([]);
  const [scans, setScans] = useState<ScanJob[]>([]);
  const [runningSourceId, setRunningSourceId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingSourceId = useRef<string | null>(null);

  function fetchAll() {
    api.get<Source[]>("/sources/").then((res) => setSources(res.data)).catch(() => setSources([]));
    api.get<ScanJob[]>("/scans/").then((res) => setScans(res.data)).catch(() => setScans([]));
  }

  useEffect(fetchAll, []);

  async function toggleSource(source: Source) {
    await api.patch(`/sources/${source.id}`, { is_enabled: !source.is_enabled });
    fetchAll();
  }

  function triggerScan(source: Source) {
    if (source.collector_type === "csv_upload") {
      pendingSourceId.current = source.id;
      fileInputRef.current?.click();
      return;
    }
    runScan(source.id);
  }

  async function runScan(sourceId: string, file?: File) {
    setRunningSourceId(sourceId);
    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      await api.post(`/scans/${sourceId}/run`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      fetchAll();
    } finally {
      setRunningSourceId(null);
    }
  }

  function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file && pendingSourceId.current) {
      runScan(pendingSourceId.current, file);
    }
    e.target.value = "";
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
        Data Collection
      </h2>
      <input type="file" ref={fileInputRef} className="hidden" accept=".csv,.xlsx,.xls" onChange={handleFileChosen} />

      <div className="mb-6 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2 text-left">Source</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Last Scan</th>
              <th className="px-4 py-2 text-left">Collected</th>
              <th className="px-4 py-2 text-left">Enabled</th>
              <th className="px-4 py-2 text-left">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {sources.map((s) => (
              <tr key={s.id} className="bg-white dark:bg-gray-950">
                <td className="px-4 py-2">
                  <div className="font-medium text-gray-800 dark:text-gray-100">{s.name}</div>
                  {!s.is_enabled && s.disabled_reason && (
                    <div className="text-xs text-gray-400 max-w-xs">{s.disabled_reason}</div>
                  )}
                  {s.last_error && (
                    <div className="text-xs text-red-500 max-w-xs truncate">{s.last_error}</div>
                  )}
                </td>
                <td className="px-4 py-2">
                  {s.is_enabled ? (
                    <span className="text-green-600 text-xs font-medium">Active</span>
                  ) : (
                    <span className="text-gray-400 text-xs font-medium">Disabled</span>
                  )}
                </td>
                <td className="px-4 py-2 text-xs text-gray-500">
                  {s.last_successful_scan_at ? new Date(s.last_successful_scan_at).toLocaleString() : "Never"}
                </td>
                <td className="px-4 py-2">{s.listings_collected_count}</td>
                <td className="px-4 py-2">
                  <input type="checkbox" checked={s.is_enabled} onChange={() => toggleSource(s)} />
                </td>
                <td className="px-4 py-2">
                  {s.is_enabled && (
                    <button
                      onClick={() => triggerScan(s)}
                      disabled={runningSourceId === s.id}
                      className="text-xs text-brand-600 dark:text-brand-500 hover:underline disabled:opacity-50"
                    >
                      {runningSourceId === s.id ? "Running…" : "Run Scan"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="mb-3 text-sm font-medium text-gray-600 dark:text-gray-300">Scan History</h3>
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Discovered</th>
              <th className="px-4 py-2 text-left">New</th>
              <th className="px-4 py-2 text-left">Updated</th>
              <th className="px-4 py-2 text-left">Duplicates</th>
              <th className="px-4 py-2 text-left">Errors</th>
              <th className="px-4 py-2 text-left">Finished</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {scans.map((s) => (
              <tr key={s.id} className="bg-white dark:bg-gray-950">
                <td className="px-4 py-2"><StatusPill status={s.status} /></td>
                <td className="px-4 py-2">{s.listings_discovered}</td>
                <td className="px-4 py-2">{s.new_listings}</td>
                <td className="px-4 py-2">{s.updated_listings}</td>
                <td className="px-4 py-2">{s.duplicate_listings}</td>
                <td className="px-4 py-2">{s.error_count}</td>
                <td className="px-4 py-2 text-xs text-gray-500">
                  {s.finished_at ? new Date(s.finished_at).toLocaleString() : "–"}
                </td>
              </tr>
            ))}
            {scans.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-400">
                  No scans yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
