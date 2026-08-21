import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Property } from "@/types/property";

interface Notifications {
  follow_ups_due: Property[];
  new_hot_listings: Property[];
  updated_since_yesterday: Property[];
}

function NotificationSection({ title, items }: { title: string; items: Property[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mb-4 last:mb-0">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {title} ({items.length})
      </div>
      <ul className="space-y-1">
        {items.slice(0, 5).map((p) => (
          <li
            key={p.id}
            className="rounded-md bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-700 dark:text-gray-200"
          >
            {p.address ?? "Unknown address"} — {p.suburb ?? ""}
            <span className="ml-2 text-xs text-brand-600 dark:text-brand-500">
              score {p.lead_score}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function NotificationsPanel() {
  const [data, setData] = useState<Notifications | null>(null);

  useEffect(() => {
    api
      .get<Notifications>("/notifications/")
      .then((res) => setData(res.data))
      .catch(() => setData(null));
  }, []);

  const isEmpty =
    !data ||
    (data.follow_ups_due.length === 0 &&
      data.new_hot_listings.length === 0 &&
      data.updated_since_yesterday.length === 0);

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-600 dark:text-gray-300">Reminders</h3>
      {isEmpty ? (
        <p className="text-sm text-gray-400">Nothing needs your attention right now.</p>
      ) : (
        <>
          <NotificationSection title="Follow-ups due" items={data!.follow_ups_due} />
          <NotificationSection title="New hot listings" items={data!.new_hot_listings} />
          <NotificationSection title="Updated since yesterday" items={data!.updated_since_yesterday} />
        </>
      )}
    </div>
  );
}
