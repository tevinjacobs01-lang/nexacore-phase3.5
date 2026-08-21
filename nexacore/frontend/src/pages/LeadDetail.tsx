import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "@/lib/api";
import type { Property } from "@/types/property";
import type { Contact } from "@/types/contact";
import type { Interaction, TaskItem, FollowUp, Appointment, Template } from "@/types/crm";
import { INTERACTION_TYPES, INTERACTION_DIRECTIONS } from "@/types/crm";
import NotesPanel from "@/components/crm/NotesPanel";
import AttachmentsPanel from "@/components/crm/AttachmentsPanel";

interface LeadOut {
  id: string; property_id: string; contact_id: string | null; status: string;
  priority: string; assigned_agent_id: string | null; next_follow_up: string | null;
  notes: string | null; created_at: string;
}
interface StageHistoryEntry { from_stage: string | null; to_stage: string; changed_at: string; }
interface AssignmentEntry { id: string; agent_id: string; assigned_by: string | null; is_current: boolean; assigned_at: string; }
interface LeadDetailResponse {
  lead: LeadOut; property: Property | null; contact: Contact | null;
  activity_timeline: Interaction[]; tasks: TaskItem[]; follow_ups: FollowUp[];
  appointments: Appointment[]; stage_history: StageHistoryEntry[];
}

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<LeadDetailResponse | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [renderedTemplate, setRenderedTemplate] = useState<string | null>(null);
  const [newInteraction, setNewInteraction] = useState({ interaction_type: "call", direction: "outgoing", outcome: "" });
  const [assignmentHistory, setAssignmentHistory] = useState<AssignmentEntry[]>([]);
  const [agentIdInput, setAgentIdInput] = useState("");
  const [assignError, setAssignError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  function fetchAll() {
    if (!id) return;
    api.get<LeadDetailResponse>(`/leads/${id}/detail`).then((res) => setData(res.data)).catch(() => setLoadError("Could not load this lead."));
    api.get<Template[]>("/templates/").then((res) => setTemplates(res.data)).catch(() => {});
    api.get<AssignmentEntry[]>(`/leads/${id}/assignment-history`).then((res) => setAssignmentHistory(res.data)).catch(() => {});
  }

  useEffect(fetchAll, [id]);

  async function handleAssign() {
    if (!id || !agentIdInput.trim()) return;
    setAssignError(null);
    try {
      await api.post(`/leads/${id}/assign`, { agent_id: agentIdInput.trim() });
      setAgentIdInput("");
      fetchAll();
    } catch (err: any) {
      setAssignError(err?.response?.data?.detail ?? "Could not assign lead — check the agent id is a valid user.");
    }
  }

  async function logInteraction() {
    if (!id || !data) return;
    await api.post("/interactions/", { ...newInteraction, lead_id: id, contact_id: data.lead.contact_id });
    setNewInteraction({ interaction_type: "call", direction: "outgoing", outcome: "" });
    fetchAll();
  }

  async function renderTemplate(templateId: string) {
    const { data: rendered } = await api.post(`/templates/${templateId}/render`, { lead_id: id });
    setRenderedTemplate(rendered.body);
  }

  if (loadError) return <p className="text-red-600">{loadError}</p>;
  if (!data) return <p className="text-gray-400">Loading…</p>;
  const { lead, property, contact, activity_timeline, tasks, follow_ups, appointments, stage_history } = data;

  return (
    <div className="max-w-4xl space-y-4">
      {/* Header: who / what property / status */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
              {contact?.name ?? "No contact"} — {property?.address ?? "Unknown property"}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {property?.suburb} · {contact?.phone ?? ""} · {contact?.email ?? ""}
            </p>
          </div>
          <div className="text-right">
            <span className="inline-block rounded-full bg-brand-50 dark:bg-brand-700/20 px-3 py-1 text-xs font-medium text-brand-700 dark:text-brand-500">
              {lead.status.replace(/_/g, " ")}
            </span>
            <div className="mt-1 text-xs text-gray-400">Priority: {lead.priority}</div>
          </div>
        </div>
      </div>

      {/* What happened previously */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Activity Timeline</h3>
        <div className="mb-3 flex flex-wrap gap-2 items-end">
          <select
            value={newInteraction.interaction_type}
            onChange={(e) => setNewInteraction({ ...newInteraction, interaction_type: e.target.value })}
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1 text-xs"
          >
            {INTERACTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select
            value={newInteraction.direction}
            onChange={(e) => setNewInteraction({ ...newInteraction, direction: e.target.value })}
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1 text-xs"
          >
            {INTERACTION_DIRECTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <input
            placeholder="Outcome…" value={newInteraction.outcome}
            onChange={(e) => setNewInteraction({ ...newInteraction, outcome: e.target.value })}
            className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1 text-xs"
          />
          <button onClick={logInteraction} className="rounded-md bg-brand-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700">
            Log
          </button>
        </div>
        <ul className="space-y-1">
          {activity_timeline.map((i) => (
            <li key={i.id} className="text-sm border-l-2 border-brand-500 pl-3">
              {i.interaction_type} ({i.direction}) {i.outcome && `— ${i.outcome}`}
              <div className="text-xs text-gray-400">{new Date(i.occurred_at).toLocaleString()}</div>
            </li>
          ))}
          {activity_timeline.length === 0 && <p className="text-sm text-gray-400">No activity yet.</p>}
        </ul>
      </div>

      {/* Pipeline stage history */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Stage History</h3>
        <ol className="space-y-1 text-sm">
          {stage_history.map((h, idx) => (
            <li key={idx} className="text-gray-600 dark:text-gray-300">
              {h.from_stage ?? "(created)"} → <span className="font-medium">{h.to_stage}</span>
              <span className="text-xs text-gray-400"> · {new Date(h.changed_at).toLocaleString()}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* What should I do next: tasks, follow-ups, appointments */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Tasks</h3>
          <ul className="space-y-1 text-sm">
            {tasks.map((t) => (
              <li key={t.id} className="text-gray-600 dark:text-gray-300">
                {t.title} <span className="text-xs text-gray-400">({t.status}, {t.priority})</span>
              </li>
            ))}
            {tasks.length === 0 && <p className="text-xs text-gray-400">None</p>}
          </ul>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Follow-ups (when to follow up)</h3>
          <ul className="space-y-1 text-sm">
            {follow_ups.map((f) => (
              <li key={f.id} className="text-gray-600 dark:text-gray-300">
                {f.follow_up_type} <span className="text-xs text-gray-400">due {new Date(f.due_at).toLocaleDateString()}</span>
              </li>
            ))}
            {follow_ups.length === 0 && <p className="text-xs text-gray-400">None</p>}
          </ul>
        </div>

        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Appointments</h3>
          <ul className="space-y-1 text-sm">
            {appointments.map((a) => (
              <li key={a.id} className="text-gray-600 dark:text-gray-300">
                {a.appointment_type} <span className="text-xs text-gray-400">{new Date(a.starts_at).toLocaleString()} ({a.status})</span>
              </li>
            ))}
            {appointments.length === 0 && <p className="text-xs text-gray-400">None</p>}
          </ul>
        </div>
      </div>

      {/* Communication templates */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Communication Templates</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {templates.map((t) => (
            <button
              key={t.id}
              onClick={() => renderTemplate(t.id)}
              className="rounded-full border border-gray-300 dark:border-gray-700 px-3 py-1 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              {t.name}
            </button>
          ))}
        </div>
        {renderedTemplate && (
          <div className="rounded-md bg-gray-50 dark:bg-gray-800 p-3 text-sm whitespace-pre-wrap">{renderedTemplate}</div>
        )}
      </div>

      {/* Assignment (Sprint 28) */}
      <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Assignment</h3>
        <p className="mb-2 text-sm text-gray-600 dark:text-gray-300">
          Currently assigned to: {lead.assigned_agent_id ?? <span className="text-gray-400">Unassigned</span>}
        </p>
        <div className="mb-2 flex gap-2">
          <input
            value={agentIdInput}
            onChange={(e) => setAgentIdInput(e.target.value)}
            placeholder="Agent user id (UUID)…"
            className="flex-1 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-xs font-mono"
          />
          <button onClick={handleAssign} className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700">
            Assign
          </button>
        </div>
        <p className="mb-2 text-xs text-gray-400">
          No agent picker exists yet — there's no API to list users. Paste a known agent's user id directly.
        </p>
        {assignError && <p className="mb-2 text-xs text-red-600">{assignError}</p>}
        {assignmentHistory.length > 0 && (
          <ul className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
            {assignmentHistory.map((a) => (
              <li key={a.id}>
                {a.agent_id} {a.is_current && <span className="text-brand-600 dark:text-brand-500">(current)</span>} — {new Date(a.assigned_at).toLocaleString()}
              </li>
            ))}
          </ul>
        )}
      </div>

      <NotesPanel entityType="lead" entityId={lead.id} />
      <AttachmentsPanel entityType="lead" entityId={lead.id} />

      {lead.notes && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          <h3 className="mb-1 text-sm font-medium text-gray-600 dark:text-gray-300">Lead Notes (legacy field)</h3>
          <p className="text-sm text-gray-600 dark:text-gray-300">{lead.notes}</p>
        </div>
      )}
    </div>
  );
}
