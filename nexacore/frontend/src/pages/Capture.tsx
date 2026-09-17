import {
  ChangeEvent,
  ClipboardEvent,
  DragEvent,
  FormEvent,
  useEffect,
  useState,
} from "react";
import { api } from "@/lib/api";
import { useNavigate, useSearchParams } from "react-router-dom";

type CaptureData = {
  address: string | null;
  suburb: string | null;
  city: string | null;
  province: string | null;
  postal_code: string | null;
  listing_reference: string | null;
  agent_name: string | null;
  agency_name: string | null;
  listing_type: string | null;
  property_type: string | null;
  asking_price: number | null;
  monthly_rental: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  garages: number | null;
  floor_size_sqm: number | null;
  stand_size_sqm: number | null;
  notes: string | null;
  seller_type: string | null;
  is_owner_listed: boolean | null;
  contact_name: string | null;
  contact_number: string | null;
  email: string | null;
  source_url: string | null;
  portal_contact_methods: string[] | null;
  owner_evidence: string | null;
};
type CaptureRecord = {
  id: string;
  original_filename: string;
  status: string;
  extraction_method: string;
  extracted_data: CaptureData;
  extraction_notes: string | null;
  property_id: string | null;
  opportunity_id: string | null;
  review_status: string;
  extraction_status: string;
  extracted_field_confidence: Record<string, string>;
  extracted_candidates: Record<string, string[]>;
  raw_text_detected: boolean;
  qualification_status: string | null;
  classification: string | null;
  crm_status: string;
  promotion_eligible: boolean;
  promotion_block_reason: string | null;
  lead_id: string | null;
  lead_status: string | null;
  created_at: string;
};

const emptyData: CaptureData = {
  address: null,
  suburb: null,
  city: null,
  province: null,
  postal_code: null,
  listing_reference: null,
  agent_name: null,
  agency_name: null,
  listing_type: null,
  property_type: null,
  asking_price: null,
  monthly_rental: null,
  bedrooms: null,
  bathrooms: null,
  garages: null,
  floor_size_sqm: null,
  stand_size_sqm: null,
  notes: null,
  seller_type: null,
  is_owner_listed: null,
  contact_name: null,
  contact_number: null,
  email: null,
  source_url: null,
  portal_contact_methods: null,
  owner_evidence: null,
};

export default function Capture() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [files, setFiles] = useState<File[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [visibleText, setVisibleText] = useState("");
  const [data, setData] = useState<CaptureData>(emptyData);
  const [captures, setCaptures] = useState<CaptureRecord[]>([]);
  const [selected, setSelected] = useState<CaptureRecord | null>(null);
  const [evidenceUrl, setEvidenceUrl] = useState<string | null>(null);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [status, setStatus] = useState("Ready for a screenshot");
  const [error, setError] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sharing, setSharing] = useState(false);

  function loadCaptures() {
    api
      .get<CaptureRecord[]>("/captures/")
      .then(({ data }) => setCaptures(data))
      .catch(() => setCaptures([]));
  }
  // Initial load: restore the deep-linked capture (?id=) so a refresh does not
  // silently switch the user to a different pending capture.
  useEffect(() => {
    api
      .get<CaptureRecord[]>("/captures/")
      .then(({ data }) => {
        setCaptures(data);
        const id = searchParams.get("id");
        const found = id ? data.find((item) => item.id === id) : undefined;
        if (found) {
          setSelected(found);
          setData({ ...emptyData, ...found.extracted_data });
        }
      })
      .catch(() => setCaptures([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function statusForCapture(item: CaptureRecord) {
    return item.crm_status === "promoted"
      ? `Promoted to CRM - ${item.lead_status ?? "new"}`
      : item.status === "saved"
        ? "Saved - awaiting qualification"
        : item.review_status === "declined"
          ? "Capture declined"
          : "Evidence uploaded - review required";
  }

  function selectCapture(item: CaptureRecord) {
    setSelected(item);
    setData({ ...emptyData, ...item.extracted_data });
    setStatus(statusForCapture(item));
    setFiles([]);
    setPreview(null);
    setError(null);
    setSearchParams({ id: item.id });
  }

  // Load the stored screenshot/evidence for the selected capture so the
  // reviewer can see the original source evidence without re-uploading it.
  useEffect(() => {
    if (!selected) {
      setEvidenceUrl(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoadingEvidence(true);
    api
      .get(`/captures/${selected.id}/evidence`, { responseType: "blob" })
      .then(({ data }) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(data as Blob);
        setEvidenceUrl(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setEvidenceUrl(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingEvidence(false);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selected?.id]);

  function chooseImages(nextFiles: FileList | File[] | undefined) {
    const norm = Array.from(nextFiles ?? []);
    const valid = norm.filter((file) => file.type.startsWith("image/"));
    if (valid.length === 0) {
      setError("Please choose one or more image files.");
      return;
    }
    setFiles((prev) => [
      ...prev,
      ...valid.filter(
        (file) =>
          !prev.some(
            (existing) =>
              existing.name === file.name && existing.size === file.size,
          ),
      ),
    ]);
    setPreview(URL.createObjectURL(valid[0]));
    setError(null);
    setStatus("Ready to read the visible listing details");
  }
  function removeImage(name: string) {
    setFiles((prev) => prev.filter((file) => file.name !== name));
    if (files.length <= 1) setPreview(null);
  }
  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    chooseImages(event.dataTransfer.files);
  }
  function onPaste(event: ClipboardEvent<HTMLDivElement>) {
    chooseImages(Array.from(event.clipboardData.files));
  }
  function update(field: keyof CaptureData, value: string) {
    setData({ ...data, [field]: value || null });
  }

  async function extract(event: FormEvent) {
    event.preventDefault();
    if (extracting) return;
    if (files.length === 0) {
      setError("Upload at least one listing screenshot first.");
      return;
    }
    setExtracting(true);
    setStatus("Reading listing image and extracting visible details...");
    setError(null);
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    if (visibleText.trim()) form.append("visible_text", visibleText);
    try {
      const response = await api.post<CaptureRecord>("/captures/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setSelected(response.data);
      setData({ ...emptyData, ...response.data.extracted_data });
      setSearchParams({ id: response.data.id });
      const detectedFieldCount = Object.entries(response.data.extracted_data)
        .filter(([key, value]) => !key.startsWith("_") && value !== null && value !== "")
        .length;
      setStatus(
        detectedFieldCount > 0
          ? `${detectedFieldCount} listing details extracted - review every field before saving.`
          : response.data.extraction_status === "unavailable"
            ? "Image reading is not configured. Review the screenshot manually or configure OCR/Vision."
            : "No listing text was detected. Please review the screenshot manually and enter the visible details.",
      );
      setFiles([]);
      setPreview(null);
      loadCaptures();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || "The screenshot could not be captured.",
      );
      setStatus("Capture needs attention");
    } finally {
      setExtracting(false);
    }
  }

  async function saveOpportunity() {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.patch<CaptureRecord>(
        `/captures/${selected.id}`,
        { extracted_data: data },
      );
      setSelected(response.data);
      setData(response.data.extracted_data);
      setStatus(
        response.data.crm_status === "promoted"
          ? `Lead created successfully - added to the ${response.data.lead_status ?? "new"} pipeline.`
          : response.data.promotion_eligible
            ? "Listing saved - ready for CRM promotion."
            : `Listing saved - CRM promotion is currently blocked: ${response.data.promotion_block_reason ?? "review is required"}`,
      );
      loadCaptures();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          "Complete the required listing fields before saving.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function declineCapture() {
    if (!selected || selected.status === "saved") return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.post<CaptureRecord>(
        `/captures/${selected.id}/decline`,
      );
      setSelected(response.data);
      setStatus("Capture declined - evidence retained");
      loadCaptures();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail || "The capture could not be declined.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function shareCapture() {
    if (!navigator.share) {
      setError("Sharing is not supported by this browser.");
      return;
    }
    setSharing(true);
    try {
      await navigator.share({
        title: "NexaCore Capture",
        text: selected
          ? `Review capture: ${selected.original_filename}`
          : "Capture a property listing in NexaCore",
      });
    } catch (err: any) {
      if (err?.name !== "AbortError")
        setError("The capture could not be shared.");
    } finally {
      setSharing(false);
    }
  }

  const fields: Array<[keyof CaptureData, string]> = [
    ["address", "Address"],
    ["suburb", "Suburb"],
    ["city", "City"],
    ["province", "Province"],
    ["property_type", "Property type"],
    ["listing_reference", "Listing reference"],
    ["agent_name", "Agent"],
    ["agency_name", "Agency"],
    ["source_url", "Original listing URL"],
    ["contact_name", "Contact name"],
    ["contact_number", "Phone"],
    ["email", "Email"],
    ["owner_evidence", "Owner evidence"],
  ];
  const stageLabels = [
    "Screenshot",
    "Image reading",
    "Structured details",
    "Duplicate check",
    "Opportunity scoring",
    "Review screen",
  ];
  const activeStage = selected ? 5 : files.length > 0 ? 1 : 0;
  return (
    <div className="space-y-6">
      <header className="nc-page-header">
        <div>
          <div className="nc-eyebrow">NexaCore Capture</div>
          <h1 className="nc-page-title">Capture a property listing</h1>
          <p className="nc-page-subtitle">
            Read visible listing information from a screenshot, then review and correct structured details before creating CRM records.
          </p>
        </div>
      </header>
      {error && (
        <p
          role="alert"
          className="rounded-xl border border-danger-200 bg-danger-50 px-4 py-3 text-sm text-danger-700 dark:border-danger-900/60 dark:bg-danger-950/30 dark:text-danger-300"
        >
          {error}
        </p>
      )}
      <div className="nc-surface overflow-x-auto p-4">
        <div className="flex min-w-[680px] items-center justify-between gap-2">
          {stageLabels.map((label, index) => (
            <div key={label} className="flex items-center gap-2">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${index <= activeStage ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-400 dark:bg-gray-800"}`}
              >
                {index < activeStage ? "✓" : index + 1}
              </div>
              <span
                className={`whitespace-nowrap text-xs font-medium ${index <= activeStage ? "text-gray-800 dark:text-gray-200" : "text-gray-400"}`}
              >
                {label}
              </span>
              {index < stageLabels.length - 1 && (
                <span className="mx-1 h-px w-5 bg-gray-200 dark:bg-gray-700" />
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
        <section className="nc-surface p-5 sm:p-7">
          <form onSubmit={extract} className="space-y-5">
            <div
              onDragOver={(event) => event.preventDefault()}
              onDrop={onDrop}
              onPaste={onPaste}
              tabIndex={0}
              className="nc-focus rounded-2xl border-2 border-dashed border-info-300 bg-info-50/50 p-8 text-center dark:border-cyan-900 dark:bg-cyan-950/20"
            >
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-xl font-semibold text-white shadow-lg shadow-brand-600/20">
                ✦
              </div>
              <h2 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                Drop or paste listing screenshots
              </h2>
              <p className="mt-2 text-sm text-gray-500">
                All selected images are grouped as one capture and kept as
                source evidence. NexaCore reads visible listing information when OCR or Vision is configured; every result still requires human review.
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                <label className="inline-flex cursor-pointer rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700">
                  Upload screenshots
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      chooseImages(event.target.files ?? undefined)
                    }
                  />
                </label>
                <label className="inline-flex cursor-pointer rounded-lg border border-brand-300 px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50 dark:border-cyan-800 dark:text-cyan-300 dark:hover:bg-cyan-950/30">
                  Take photo
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    multiple
                    className="hidden"
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                      chooseImages(event.target.files ?? undefined)
                    }
                  />
                </label>
                {
                  <button
                    type="button"
                    onClick={shareCapture}
                    disabled={sharing}
                    className="nc-focus rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                  >
                    {sharing ? "Sharing..." : "Share"}
                  </button>
                }
              </div>
              {files.length > 0 && (
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {files.map((file) => (
                    <div
                      key={`${file.name}-${file.size}`}
                      className="flex items-center gap-2 rounded-full border border-info-200 bg-white px-3 py-1 text-xs text-info-700 dark:border-cyan-900 dark:bg-gray-900 dark:text-cyan-300"
                    >
                      <span>{file.name}</span>
                      <button
                        type="button"
                        onClick={() => removeImage(file.name)}
                        className="font-bold"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Visible text, if available
              <span className="ml-2 text-xs font-normal text-gray-400">
                Optional supporting text
              </span>
              <textarea
                value={visibleText}
                onChange={(event) => setVisibleText(event.target.value)}
                rows={4}
                placeholder="Optional: paste any text that OCR may miss..."
                className="nc-focus mt-2 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
              />
            </label>
            {preview && (
              <img
                src={preview}
                alt="Uploaded listing screenshot preview"
                className="max-h-80 w-full rounded-xl border border-gray-200 object-contain dark:border-gray-800"
              />
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p aria-live="polite" className="text-sm text-gray-500">
                {status}
              </p>
              <button
                disabled={files.length === 0 || extracting}
                className="nc-focus rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {extracting
                  ? "Reading image..."
                  : selected
                    ? "Read image again"
                    : "Read listing image"}
              </button>
            </div>
          </form>
        </section>
        <aside className="space-y-4">
          <section className="nc-surface p-5">
            <div className="nc-eyebrow">Review before creation</div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Listing detected
            </h2>
            <p className="mt-2 text-sm text-gray-500">
              Evidence is uploaded first. Review and complete the supplied-text
              details before creating a property, opportunity, or CRM lead.
            </p>
            {selected && (
              <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <div className="mb-2 font-semibold text-brand-700 dark:text-cyan-300">
                  Reviewing: {selected.original_filename}
                </div>
                {loadingEvidence && (
                  <p className="mb-2 text-slate-400">Loading evidence...</p>
                )}
                {evidenceUrl && (
                  <img
                    src={evidenceUrl}
                    alt={`Source evidence for ${selected.original_filename}`}
                    className="mb-2 max-h-64 w-full rounded-lg border border-slate-200 object-contain dark:border-slate-800"
                  />
                )}
                <div className="font-semibold text-slate-900 dark:text-white">
                  {selected.crm_status === "promoted"
                    ? `Promoted to CRM - lead is ${selected.lead_status ?? "new"}.`
                    : selected.promotion_eligible
                      ? "Qualified and ready for CRM promotion."
                      : selected.review_status === "declined"
                        ? "Capture declined. Evidence is retained."
                        : selected.status === "saved"
                          ? "Saved - awaiting qualification before CRM promotion."
                          : "Evidence uploaded - review required."}
                </div>
                {selected.promotion_block_reason && (
                  <div className="mt-1 text-slate-500 dark:text-slate-400">
                    {selected.promotion_block_reason}
                  </div>
                )}
                <div className="mt-2 text-slate-500 dark:text-slate-400">
                  Extraction: {selected.extraction_method.replace(/_/g, " ")} · {selected.extraction_status.replace(/_/g, " ")} · {selected.raw_text_detected ? "text detected" : "no text detected"}
                </div>
                {selected.lead_id && <button type="button" onClick={() => navigate(`/leads/${selected.lead_id}`)} className="mt-2 font-semibold text-cyan-700 hover:underline dark:text-cyan-300">Open existing CRM Lead</button>}
                {!selected.lead_id && selected.opportunity_id && <button type="button" onClick={() => navigate("/discovery")} className="mt-2 font-semibold text-cyan-700 hover:underline dark:text-cyan-300">Review in Discovery</button>}
              </div>
            )}
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/60">
                <span className="block text-gray-400">Listing type</span>
                <select
                  value={data.listing_type || ""}
                  onChange={(event) =>
                    update("listing_type", event.target.value)
                  }
                  className="mt-1 w-full bg-transparent font-semibold text-gray-800 dark:text-gray-100"
                >
                  <option value="">Needs review</option>
                  <option value="sale">Sale</option>
                  <option value="rent">Rental</option>
                </select>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-800/60">
                <span className="block text-gray-400">Listed by</span>
                <select
                  value={data.seller_type || ""}
                  onChange={(event) =>
                    update("seller_type", event.target.value)
                  }
                  className="mt-1 w-full bg-transparent font-semibold capitalize text-gray-800 dark:text-gray-100"
                >
                  <option value="">Unknown</option>
                  <option value="owner">Owner</option>
                  <option value="agent">Agent</option>
                  <option value="agency">Agency</option>
                  <option value="developer">Developer</option>
                </select>
              </div>
            </div>
            <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-600 dark:bg-gray-800/60 dark:text-gray-300">
              <span className="block font-medium text-gray-400">Portal contact availability</span>
              <div className="mt-2 flex flex-wrap gap-3">
                {(["WhatsApp Agent", "Call Agent", "Email Agent", "Contact Agent"] as const).map((method) => (
                  <label key={method} className="flex items-center gap-1.5">
                    <input
                      type="checkbox"
                      checked={data.portal_contact_methods?.includes(method) ?? false}
                      onChange={(event) => {
                        const current = data.portal_contact_methods ?? [];
                        setData({
                          ...data,
                          portal_contact_methods: event.target.checked
                            ? [...current, method]
                            : current.filter((item) => item !== method),
                        });
                      }}
                    />
                    {method}
                  </label>
                ))}
              </div>
            </div>
            {selected?.extraction_notes && (
              <p className="mt-4 rounded-lg bg-warning-50 p-3 text-xs text-warning-700 dark:bg-warning-700/10 dark:text-warning-300">
                {selected.extraction_notes}
              </p>
            )}
          </section>
          <section className="nc-surface p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.16em] text-gray-400">
              Structured details
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {fields.map(([field, label]) => (
                <label
                  key={field}
                  className="text-xs font-medium text-gray-600 dark:text-gray-300"
                >
                  {label}
                  <input
                    value={data[field] == null ? "" : String(data[field])}
                    onChange={(event) => update(field, event.target.value)}
                    className="nc-focus mt-1 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
                  />
                </label>
              ))}
              <label className="text-xs font-medium text-gray-600 dark:text-gray-300">
                Price
                <input
                  type="number"
                  value={
                    data.listing_type === "rent"
                      ? (data.monthly_rental ?? "")
                      : (data.asking_price ?? "")
                  }
                  onChange={(event) =>
                    setData({
                      ...data,
                      ...(data.listing_type === "rent"
                        ? {
                            monthly_rental: event.target.value
                              ? Number(event.target.value)
                              : null,
                          }
                        : {
                            asking_price: event.target.value
                              ? Number(event.target.value)
                              : null,
                          }),
                    })
                  }
                  className="nc-focus mt-1 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
                />
              </label>
              {(
                [
                  ["bedrooms", "Bedrooms"],
                  ["bathrooms", "Bathrooms"],
                  ["garages", "Parking"],
                ] as const
              ).map(([field, label]) => (
                <label
                  key={field}
                  className="text-xs font-medium text-gray-600 dark:text-gray-300"
                >
                  {label}
                  <input
                    type="number"
                    min="0"
                    value={data[field] ?? ""}
                    onChange={(event) =>
                      setData({
                        ...data,
                        [field]: event.target.value
                          ? Number(event.target.value)
                          : null,
                      })
                    }
                    className="nc-focus mt-1 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
                  />
                </label>
              ))}
              {(
                [
                  ["floor_size_sqm", "Property size (m2)"],
                  ["stand_size_sqm", "Land size (m2)"],
                ] as const
              ).map(([field, label]) => (
                <label
                  key={field}
                  className="text-xs font-medium text-gray-600 dark:text-gray-300"
                >
                  {label}
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={data[field] ?? ""}
                    onChange={(event) =>
                      setData({
                        ...data,
                        [field]: event.target.value
                          ? Number(event.target.value)
                          : null,
                      })
                    }
                    className="nc-focus mt-1 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
                  />
                </label>
              ))}
            </div>
            <label className="mt-3 block text-xs font-medium text-gray-600 dark:text-gray-300">
              Description / notes
              <textarea
                value={data.notes || ""}
                onChange={(event) => update("notes", event.target.value)}
                rows={3}
                className="nc-focus mt-1 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
              />
            </label>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                disabled={!selected || saving || selected.status === "saved"}
                onClick={saveOpportunity}
                className="nc-focus flex-1 rounded-lg bg-success-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-success-700 disabled:opacity-50"
              >
                {saving
                  ? "Saving..."
                  : selected?.status === "saved"
                    ? "Saved"
                    : "Accept / create"}
              </button>
              <button
                type="button"
                disabled={!selected || saving || selected.status === "saved"}
                onClick={declineCapture}
                className="nc-focus rounded-lg border border-danger-300 px-3 py-2.5 text-sm font-semibold text-danger-700 hover:bg-danger-50 dark:border-danger-800 dark:text-danger-300 dark:hover:bg-danger-950/30"
              >
                Decline
              </button>
            </div>
          </section>
        </aside>
      </div>
      <section className="nc-surface overflow-hidden">
        <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Recent captures
          </h2>
          <p className="mt-1 text-xs text-gray-500">
            Your screenshot evidence and review status
          </p>
        </div>
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {captures.length === 0 ? (
            <p className="p-5 text-sm text-gray-500">No captures yet.</p>
          ) : (
            captures.map((item) => {
              const isPendingReview = item.review_status === "review_required";
              const isSelected = selected?.id === item.id;
              return (
                <div
                  key={item.id}
                  className={`flex flex-wrap items-center justify-between gap-3 p-4 ${isSelected ? "bg-brand-50/60 dark:bg-cyan-950/20" : ""}`}
                >
                  <div className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-gray-800 dark:text-gray-100">
                      {item.original_filename}
                      {isSelected && (
                        <span className="ml-2 text-xs font-semibold text-brand-600 dark:text-cyan-300">
                          Selected
                        </span>
                      )}
                    </span>
                    <span className="mt-1 block text-xs text-gray-500">
                      {new Date(item.created_at).toLocaleString()} ·{" "}
                      {item.extraction_method.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full bg-warning-50 px-2.5 py-1 text-xs font-medium capitalize text-warning-700 dark:bg-warning-700/10 dark:text-warning-300">
                      {item.crm_status === "promoted"
                        ? "CRM promoted"
                        : item.review_status.replace(/_/g, " ")}
                    </span>
                    <button
                      type="button"
                      onClick={() => selectCapture(item)}
                      className={`nc-focus whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold ${
                        isPendingReview
                          ? "bg-brand-600 text-white hover:bg-brand-700"
                          : "border border-gray-300 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                      }`}
                    >
                      {isPendingReview ? "Review" : "View"}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}


