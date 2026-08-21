import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "@/lib/api";
import type { Contact } from "@/types/contact";
import type { Interaction } from "@/types/crm";
import type { Property } from "@/types/property";
import NotesPanel from "@/components/crm/NotesPanel";
import AttachmentsPanel from "@/components/crm/AttachmentsPanel";

export default function ContactDetail() {
  const { id } = useParams<{ id: string }>();
  const [contact, setContact] = useState<Contact | null>(null);
  const [timeline, setTimeline] = useState<Interaction[]>([]);
  const [listings, setListings] = useState<Property[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  function fetchAll() {
    if (!id) return;
    api.get<Contact>(`/contacts/${id}`).then((res) => setContact(res.data)).catch(() => setLoadError("Could not load this contact."));
    api.get<Interaction[]>("/interactions/timeline", { params: { contact_id: id } }).then((res) => setTimeline(res.data)).catch(() => {});
    api.get<Property[]>(`/contacts/${id}/listings`).then((res) => setListings(res.data)).catch(() => {});
  }

  useEffect(fetchAll, [id]);

  if (loadError) return <p className="text-red-600">{loadError}</p>;
  if (!contact) return <p className="text-gray-400">Loading…</p>;

  return (
    <div className="max-w-3xl space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-1">{contact.name ?? "Unnamed contact"}</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {contact.contact_type?.replace(/_/g, " ") ?? "No type"} · {contact.phone ?? "no phone"} · {contact.email ?? "no email"}
        </p>
      </div>

      {listings.length > 0 && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Linked Listings</h3>
          <ul className="space-y-1 text-sm">
            {listings.map((p) => (
              <li key={p.id} className="text-gray-700 dark:text-gray-200">{p.address} — {p.suburb}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Activity Timeline</h3>
        {timeline.length === 0 && <p className="text-sm text-gray-400">No interactions yet.</p>}
        <ul className="space-y-2">
          {timeline.map((i) => (
            <li key={i.id} className="text-sm border-l-2 border-brand-500 pl-3">
              <span className="font-medium text-gray-700 dark:text-gray-200">{i.interaction_type}</span>
              <span className="text-gray-400"> ({i.direction})</span>
              {i.outcome && <span className="text-gray-500 dark:text-gray-400"> — {i.outcome}</span>}
              <div className="text-xs text-gray-400">{new Date(i.occurred_at).toLocaleString()}</div>
            </li>
          ))}
        </ul>
      </div>

      <NotesPanel entityType="contact" entityId={contact.id} />
      <AttachmentsPanel entityType="contact" entityId={contact.id} />
    </div>
  );
}
