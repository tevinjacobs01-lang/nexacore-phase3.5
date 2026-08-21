import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Attachment } from "@/types/attachment";

interface Props {
  entityType: "listing" | "contact" | "lead";
  entityId: string;
}

export default function AttachmentsPanel({ entityType, entityId }: Props) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function fetchAttachments() {
    api
      .get<Attachment[]>("/attachments/", { params: { entity_type: entityType, entity_id: entityId } })
      .then((res) => setAttachments(res.data))
      .catch(() => setError("Could not load attachments."));
  }

  useEffect(fetchAttachments, [entityType, entityId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await api.post("/attachments/", formData, {
        params: { entity_type: entityType, entity_id: entityId },
        headers: { "Content-Type": "multipart/form-data" },
      });
      fetchAttachments();
    } catch {
      setError("Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  async function handleDownload(attachment: Attachment) {
    const res = await api.get(`/attachments/${attachment.id}/download`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = attachment.original_filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-600 dark:text-gray-300">Attachments</h3>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="text-xs text-brand-600 dark:text-brand-500 hover:underline disabled:opacity-50"
        >
          {uploading ? "Uploading…" : "+ Upload file"}
        </button>
        <input type="file" ref={fileInputRef} className="hidden" onChange={handleUpload} />
      </div>

      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}

      <ul className="space-y-1">
        {attachments.map((a) => (
          <li key={a.id} className="flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-300">
              {a.original_filename}
              <span className="ml-2 text-xs text-gray-400">{(a.size_bytes / 1024).toFixed(0)} KB</span>
            </span>
            <button onClick={() => handleDownload(a)} className="text-xs text-brand-600 dark:text-brand-500 hover:underline">
              Download
            </button>
          </li>
        ))}
        {attachments.length === 0 && !error && <p className="text-xs text-gray-400">No attachments yet.</p>}
      </ul>
    </div>
  );
}
