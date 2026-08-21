import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Template } from "@/types/crm";
import { TEMPLATE_TYPES } from "@/types/crm";

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", template_type: TEMPLATE_TYPES[0], subject: "", body: "" });
  const [error, setError] = useState<string | null>(null);

  function fetchTemplates() {
    api.get<Template[]>("/templates/").then((res) => setTemplates(res.data)).catch(() => setError("Could not load templates."));
  }

  useEffect(fetchTemplates, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/templates/", form);
      setForm({ name: "", template_type: TEMPLATE_TYPES[0], subject: "", body: "" });
      setShowForm(false);
      fetchTemplates();
    } catch {
      setError("Could not save template.");
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Communication Templates</h2>
        <button onClick={() => setShowForm(!showForm)} className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
          {showForm ? "Cancel" : "+ New Template"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-4 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <input
            placeholder="Template name" value={form.name} required
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="mb-2 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
          />
          <select
            value={form.template_type}
            onChange={(e) => setForm({ ...form, template_type: e.target.value })}
            className="mb-2 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
          >
            {TEMPLATE_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
          <input
            placeholder="Subject (optional)" value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
            className="mb-2 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
          />
          <textarea
            placeholder="Body — use {{contact_name}}, {{property_address}}, {{property_price}}, {{agent_name}}, {{suburb}}, {{listing_url}}"
            value={form.body} required rows={4}
            onChange={(e) => setForm({ ...form, body: e.target.value })}
            className="mb-2 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
          />
          <button type="submit" className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
            Save Template
          </button>
        </form>
      )}

      {error && !showForm && <p className="text-sm text-red-600">{error}</p>}

      <div className="space-y-2">
        {templates.map((t) => (
          <div key={t.id} className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
            <div className="mb-1 flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-800 dark:text-gray-100">{t.name}</h3>
              <span className="text-xs text-gray-400">{t.template_type.replace(/_/g, " ")}</span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{t.body}</p>
          </div>
        ))}
        {templates.length === 0 && !error && <p className="text-sm text-gray-400">No templates yet.</p>}
      </div>
    </div>
  );
}
