import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CrmDashboardData {
  lead_metrics: Record<string, number>;
  follow_up_metrics: { due_today: number; overdue: number; upcoming: number };
  conversion_metrics: Record<string, number | null>;
  agent_metrics: {
    agent_id: string; agent_name: string; leads_count: number; activities_count: number;
    appointments_count: number; conversion_rate_pct: number | null; won_count: number;
  }[];
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      <div className="mt-1 text-xl font-semibold text-gray-900 dark:text-gray-50">{value}</div>
    </div>
  );
}

export default function CrmDashboard() {
  const [data, setData] = useState<CrmDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<CrmDashboardData>("/dashboard/crm").then((res) => setData(res.data)).catch(() => setError("Could not load the CRM dashboard."));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-gray-400">Loading…</p>;

  const fmtPct = (v: number | null) => (v === null ? "–" : `${v}%`);

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">CRM Dashboard</h2>

      <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Lead Metrics</h3>
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        {Object.entries(data.lead_metrics).map(([key, value]) => (
          <MetricCard key={key} label={key.replace(/_/g, " ")} value={value} />
        ))}
      </div>

      <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Follow-Up Metrics</h3>
      <div className="mb-6 grid grid-cols-3 gap-3">
        <MetricCard label="Due Today" value={data.follow_up_metrics.due_today} />
        <MetricCard label="Overdue" value={data.follow_up_metrics.overdue} />
        <MetricCard label="Upcoming" value={data.follow_up_metrics.upcoming} />
      </div>

      <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Conversion Metrics</h3>
      <div className="mb-6 grid grid-cols-2 sm:grid-cols-5 gap-3">
        <MetricCard label="Contact → Response" value={fmtPct(data.conversion_metrics.contact_to_response)} />
        <MetricCard label="Response → Qualified" value={fmtPct(data.conversion_metrics.response_to_qualified)} />
        <MetricCard label="Qualified → Appointment" value={fmtPct(data.conversion_metrics.qualified_to_appointment)} />
        <MetricCard label="Appointment → Won" value={fmtPct(data.conversion_metrics.appointment_to_won)} />
        <MetricCard label="Overall Conversion" value={fmtPct(data.conversion_metrics.overall_conversion_rate)} />
      </div>

      <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Agent Metrics</h3>
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2 text-left">Agent</th>
              <th className="px-4 py-2 text-left">Leads</th>
              <th className="px-4 py-2 text-left">Activities</th>
              <th className="px-4 py-2 text-left">Appointments</th>
              <th className="px-4 py-2 text-left">Conversion</th>
              <th className="px-4 py-2 text-left">Won</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.agent_metrics.map((a) => (
              <tr key={a.agent_id} className="bg-white dark:bg-gray-950">
                <td className="px-4 py-2">{a.agent_name}</td>
                <td className="px-4 py-2">{a.leads_count}</td>
                <td className="px-4 py-2">{a.activities_count}</td>
                <td className="px-4 py-2">{a.appointments_count}</td>
                <td className="px-4 py-2">{fmtPct(a.conversion_rate_pct)}</td>
                <td className="px-4 py-2">{a.won_count}</td>
              </tr>
            ))}
            {data.agent_metrics.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No agents yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
