import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Note } from "@/types/crm";

interface Props {
  entityType: "listing" | "contact" | "lead";
  entityId: string;
}

export default function NotesPanel({ entityType, entityId }: Props) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState("");
  const [isPrivate, setIsPrivate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function fetchNotes() {
    api
      .get<Note[]>("/notes/", { params: { entity_type: entityType, entity_id: entityId } })
      .then((res) => setNotes(res.data))
      .catch(() => setError("Could not load notes."));
  }

  useEffect(fetchNotes, [entityType, entityId]);

  async function addNote() {
    if (!newNote.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.post("/notes/", { entity_type: entityType, entity_id: entityId, content: newNote, is_private: isPrivate });
      setNewNote("");
      setIsPrivate(false);
      fetchNotes();
    } catch {
      setError("Could not save note.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <h3 className="mb-2 text-sm font-medium text-gray-600 dark:text-gray-300">Notes</h3>
      <div className="mb-3 flex gap-2">
        <input
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addNote()}
          placeholder="Add a note…"
          className="flex-1 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
        />
        <label className="flex items-center gap-1 text-xs text-gray-500 whitespace-nowrap">
          <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} /> Private
        </label>
        <button
          onClick={addNote}
          disabled={saving}
          className="rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          Add
        </button>
      </div>

      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}

      <ul className="space-y-2">
        {notes.map((n) => (
          <li key={n.id} className="text-sm rounded-md bg-gray-50 dark:bg-gray-800 px-3 py-2">
            {n.is_private && <span className="mr-1 text-xs text-amber-600">[private]</span>}
            {n.content}
            <div className="text-xs text-gray-400">{new Date(n.created_at).toLocaleString()}</div>
          </li>
        ))}
        {notes.length === 0 && !error && <p className="text-sm text-gray-400">No notes yet.</p>}
      </ul>
    </div>
  );
}
