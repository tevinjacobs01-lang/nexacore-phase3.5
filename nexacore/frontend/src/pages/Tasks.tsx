import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { TaskItem } from "@/types/crm";
import { TASK_PRIORITIES } from "@/types/crm";

type Tab = "today" | "overdue" | "upcoming";

export default function Tasks() {
  const [tab, setTab] = useState<Tab>("today");
  const [tasks, setTasks] = useState<TaskItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function fetchTasks() {
    setTasks(null);
    setError(null);
    api
      .get<TaskItem[]>(`/tasks/${tab}`)
      .then((res) => setTasks(res.data))
      .catch(() => setError("Could not load tasks."));
  }

  useEffect(fetchTasks, [tab]);

  async function markComplete(taskId: string) {
    await api.patch(`/tasks/${taskId}`, { status: "completed" });
    fetchTasks();
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">Tasks</h2>

      <div className="mb-4 flex gap-2">
        {(["today", "overdue", "upcoming"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
              tab === t ? "bg-brand-600 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {tasks === null && !error && <p className="text-sm text-gray-400">Loading…</p>}

      {tasks && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2 text-left">Title</th>
                <th className="px-4 py-2 text-left">Priority</th>
                <th className="px-4 py-2 text-left">Due</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {tasks.map((t) => (
                <tr key={t.id} className="bg-white dark:bg-gray-950">
                  <td className="px-4 py-2">{t.title}</td>
                  <td className="px-4 py-2 capitalize">
                    <span className={TASK_PRIORITIES.indexOf(t.priority) >= 2 ? "text-red-600 font-medium" : ""}>
                      {t.priority}
                    </span>
                  </td>
                  <td className="px-4 py-2">{t.due_date ?? "–"}</td>
                  <td className="px-4 py-2 capitalize">{t.status.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2">
                    {t.status !== "completed" && (
                      <button onClick={() => markComplete(t.id)} className="text-xs text-brand-600 dark:text-brand-500 hover:underline">
                        Mark complete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {tasks.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">No {tab} tasks.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
