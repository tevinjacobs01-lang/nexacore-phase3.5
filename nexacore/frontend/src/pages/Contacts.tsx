import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import type { Contact } from "@/types/contact";
import { CONTACT_TYPES } from "@/types/contact";

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [filterType, setFilterType] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", phone: "", email: "", contact_type: "" });
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  function fetchContacts() {
    const params = filterType ? { contact_type: filterType } : {};
    api.get<Contact[]>("/contacts/", { params }).then((res) => setContacts(res.data)).catch(() => setContacts([]));
  }

  useEffect(fetchContacts, [filterType]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/contacts/", form);
      setForm({ name: "", phone: "", email: "", contact_type: "" });
      setShowForm(false);
      fetchContacts();
    } catch (err: any) {
      if (err?.response?.status === 409) {
        setError(err.response.data.detail.message + " Use force_create to add anyway.");
      } else {
        setError("Failed to create contact.");
      }
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Contacts</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
        >
          {showForm ? "Cancel" : "+ New Contact"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-4 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
          <div className="grid grid-cols-2 gap-3 mb-3">
            <input
              placeholder="Name" value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
            />
            <select
              value={form.contact_type}
              onChange={(e) => setForm({ ...form, contact_type: e.target.value })}
              className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
            >
              <option value="">Contact type…</option>
              {CONTACT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
            <input
              placeholder="Phone" value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
            />
            <input
              placeholder="Email" value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
            />
          </div>
          <button type="submit" className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
            Create
          </button>
        </form>
      )}

      <div className="mb-3">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-1.5 text-sm"
        >
          <option value="">All types</option>
          {CONTACT_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Phone</th>
              <th className="px-4 py-2 text-left">Email</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {contacts.map((c) => (
              <tr
                key={c.id}
                onClick={() => navigate(`/contacts/${c.id}`)}
                className="cursor-pointer bg-white dark:bg-gray-950 hover:bg-gray-50 dark:hover:bg-gray-900"
              >
                <td className="px-4 py-2 font-medium text-gray-800 dark:text-gray-100">{c.name ?? "–"}</td>
                <td className="px-4 py-2">{c.contact_type?.replace(/_/g, " ") ?? "–"}</td>
                <td className="px-4 py-2">{c.phone ?? "–"}</td>
                <td className="px-4 py-2">{c.email ?? "–"}</td>
              </tr>
            ))}
            {contacts.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">No contacts yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
