import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { FollowUp } from "@/types/crm";

interface FollowUpDashboard {
  due_today: FollowUp[];
  overdue: FollowUp[];
  upcoming: FollowUp[];
  completed: FollowUp[];
}

function Section({ title, items, onComplete, tone }: {
  title: string; items: FollowUp[]; onComplete?: (id: string) => void; tone?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <h3 className={`mb-2 text-sm font-medium ${tone ?? "text-gray-600 dark:text-gray-300"}`}>
        {title} ({items.length})
      </h3>
      <ul className="space-y-2">
        {items.map((f) => (
          <li key={f.id} className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-300">
              {f.follow_up_type} — {new Date(f.due_at).toLocaleString()}
            </span>
            {onComplete && (
              <button onClick={() => onComplete(f.id)} className="text-xs text-brand-600 dark:text-brand-500 hover:underline">
                Mark done
              </button>
            )}
          </li>
        ))}
        {items.length === 0 && <p className="text-xs text-gray-400">None</p>}
      </ul>
    </div>
  );
}

export default function FollowUps() {
  const [data, setData] = useState<FollowUpDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  function fetchData() {
    api
      .get<FollowUpDashboard>("/follow-ups/dashboard")
      .then((res) => setData(res.data))
      .catch(() => setError("Could not load follow-ups."));
  }

  useEffect(fetchData, []);

  async function markComplete(id: string) {
    await api.patch(`/follow-ups/${id}`, { status: "completed" });
    fetchData();
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <p className="text-gray-400">Loading…</p>;

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Follow-ups</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section title="Overdue" items={data.overdue} onComplete={markComplete} tone="text-red-600" />
        <Section title="Due Today" items={data.due_today} onComplete={markComplete} tone="text-amber-600" />
        <Section title="Upcoming" items={data.upcoming} onComplete={markComplete} />
        <Section title="Completed" items={data.completed} />
      </div>
    </div>
  );
}
