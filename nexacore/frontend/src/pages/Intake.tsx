import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { clearPendingSharedIntake, pendingSharedIntake } from "@/lib/shareIntake";

type Intake = {
  id: string;
  input_type: "url" | "text" | "screenshot";
  source_url?: string | null;
  source_domain?: string | null;
  status: string;
  result_summary: string;
  extracted_data: Record<string, unknown>;
  property_id?: string | null;
  capture_id?: string | null;
  opportunity_id?: string | null;
  lead_id?: string | null;
  created_at: string;
};

export default function Intake() {
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [items, setItems] = useState<Intake[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = () => api.get<Intake[]>("/intakes/").then(({ data }) => setItems(data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  useEffect(() => {
    const shared = pendingSharedIntake();
    if (!shared) return;
    if (shared.kind === "text" && shared.value) {
      try {
        const parsed = new URL(shared.value);
        if (parsed.protocol === "http:" || parsed.protocol === "https:") setUrl(shared.value);
        else setText(shared.value);
      } catch { setText(shared.value); }
      setMessage("Shared listing ready for research.");
    } else if (shared.kind === "screenshot" && shared.base64) {
      try {
        const binary = atob(shared.base64);
        const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
        setImage(new File([bytes], "shared-listing", { type: shared.mimeType || "image/jpeg" }));
        setMessage("Shared screenshot ready for capture and research.");
      } catch { setMessage("The shared screenshot could not be prepared. Please share it again."); }
    }
  }, []);

  async function submit(kind: "url" | "text" | "screenshot") {
    setBusy(true);
    setMessage(kind === "url" ? "Researching original listing…" : kind === "screenshot" ? "Capturing shared screenshot…" : "Extracting shared listing text…");
    try {
      let body: { input_type: string; value?: string; capture_id?: string };
      if (kind === "screenshot") {
        if (!image) throw new Error("Choose an image first.");
        const form = new FormData(); form.append("files", image);
        const capture = await api.post<{ id: string }>("/captures/", form, { headers: { "Content-Type": "multipart/form-data" } });
        body = { input_type: "screenshot", capture_id: capture.data.id, value: url.trim() || undefined };
      } else {
        body = { input_type: kind, value: kind === "url" ? url : text };
      }
      const { data } = await api.post<Intake>("/intakes/", body);
      setMessage(data.result_summary);
      clearPendingSharedIntake();
      if (kind === "url") setUrl("");
      if (kind === "text") setText("");
      if (kind === "screenshot") setImage(null);
      load();
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || error?.message || "Intake could not be submitted.");
    } finally { setBusy(false); }
  }

  return <div className="mx-auto max-w-5xl space-y-6">
    <div><div className="nc-eyebrow">Universal intake</div><h1 className="nc-page-title">Add property material</h1><p className="nc-page-subtitle">Submit a listing URL, shared text, or screenshot. Facts are extracted for review without inventing missing details.</p></div>
    {message && <div className="rounded-lg border border-cyan-900 bg-cyan-950/40 px-4 py-3 text-sm text-cyan-100">{message}</div>}
    <div className="grid gap-4 lg:grid-cols-3">
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><h2 className="font-semibold text-white">Listing URL</h2><input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://property24.co.za/..." className="nc-input mt-4 w-full" /><button disabled={busy || !url.trim()} onClick={() => submit("url")} className="nc-button-primary mt-3 w-full">Submit URL</button></section>
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><h2 className="font-semibold text-white">Shared text</h2><textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste text from WhatsApp or email" className="nc-input mt-4 min-h-24 w-full" /><button disabled={busy || !text.trim()} onClick={() => submit("text")} className="nc-button-primary mt-3 w-full">Submit text</button></section>
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><h2 className="font-semibold text-white">Screenshot</h2><input type="file" accept="image/*" onChange={(e) => setImage(e.target.files?.[0] || null)} className="mt-4 block w-full text-sm text-slate-300" /><p className="mt-2 text-xs text-slate-400">Optionally keep a listing URL above while uploading; the screenshot remains evidence.</p><button disabled={busy || !image} onClick={() => submit("screenshot")} className="nc-button-primary mt-3 w-full">Upload screenshot</button></section>
    </div>
    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><h2 className="font-semibold text-white">Recent intakes</h2><div className="mt-4 space-y-3">{items.length === 0 ? <p className="text-sm text-slate-400">No intakes yet.</p> : items.map((item) => <div key={item.id} className="rounded-lg border border-slate-800 p-4 text-sm"><div className="flex flex-wrap justify-between gap-2"><span className="font-medium capitalize text-white">{item.input_type} · {item.status.replace(/_/g, " ")}</span><span className="text-slate-500">{new Date(item.created_at).toLocaleString()}</span></div><p className="mt-1 text-slate-300">{item.result_summary}</p>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer" className="mt-2 block text-cyan-400 hover:text-cyan-300">{item.source_domain || item.source_url}</a>}<div className="mt-2 flex gap-3">{item.capture_id && <Link to={`/capture?id=${item.capture_id}`} className="text-cyan-400">Review screenshot</Link>}{item.property_id && <Link to="/properties" className="text-cyan-400">Open property workflow</Link>}{item.opportunity_id && <Link to="/discovery" className="text-cyan-400">Open discovery</Link>}{item.lead_id && <Link to={`/leads/${item.lead_id}`} className="text-cyan-400">Open lead</Link>}</div></div>)}</div></section>
  </div>;
}


