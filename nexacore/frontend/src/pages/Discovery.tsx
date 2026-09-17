import { useEffect, useState } from "react";
import { api, getCurrentUserRole } from "@/lib/api";
import { useNavigate } from "react-router-dom";

type Classification = "seller" | "landlord" | "unknown";
type QualificationStatus =
  "unreviewed" | "review_required" | "qualified" | "not_qualified";

interface PropertyData {
  id: string;
  address: string | null;
  suburb: string | null;
  city: string | null;
  province: string | null;
  property_type: string | null;
  listing_type: string | null;
  seller_type: string | null;
  is_owner_listed: boolean | null;
  bedrooms: number | null;
  bathrooms: number | null;
  garages: number | null;
  floor_size_sqm: number | null;
  stand_size_sqm: number | null;
  asking_price: number | null;
  monthly_rental: number | null;
  listing_url: string | null;
  listing_status: string;
  lead_score: number;
  created_at: string;
}

interface ObservationData {
  id: string;
  source_id: string;
  source_listing_id: string | null;
  canonical_url: string | null;
  source_type: string | null;
  discovery_method: string | null;
  source_confidence: string;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  contact_company: string | null;
  contact_agency: string | null;
  contact_confidence: string;
  contact_availability: "direct" | "portal_mediated" | "unavailable";
  portal_contact_methods: string[];
  lifecycle_status: string;
  first_seen_at: string;
  last_seen_at: string;
  observed_at: string;
  source_updated_at: string | null;
  media: unknown[];
}

interface Opportunity {
  id: string;
  property_id: string;
  classification: Classification;
  qualification_status: QualificationStatus;
  qualification_reason: string | null;
  discovery_score: number;
  opportunity_score: number;
  signal_score: number;
  data_confidence: string;
  intelligence_reasons: string[];
  recommended_action: string | null;
  historical_signals: Array<{
    signal_type: string;
    severity: string;
    evidence: string;
    confidence: string;
    detected_at: string | null;
    source_id: string | null;
  }>;
  score_band: string;
  score_reasons: string[];
  reviewed_by: string | null;
  reviewed_at: string | null;
  crm_status: string;
  promotion_eligible: boolean;
  promotion_block_reason: string | null;
  lead_id: string | null;
  lead_status: string | null;
  property: PropertyData;
  observation: ObservationData | null;
  duplicate: { match_type: string; match_reason: string } | null;
}

interface DiscoveryEvent {
  id: string;
  event_type: string;
  property_id: string | null;
  opportunity_id: string | null;
  observation_id: string | null;
  payload: string | null;
  is_read: boolean;
  created_at: string;
}

interface Source {
  id: string;
  name: string;
}

const emptyFilters = {
  classification: "",
  qualification_status: "",
  property_type: "",
  suburb: "",
  source_id: "",
  listing_status: "",
  min_price: "",
  max_price: "",
  min_score: "",
  q: "",
  listing_type: "",
  listed_by: "",
};

function Badge({ value }: { value: string }) {
  const colors: Record<string, string> = {
    seller: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    landlord:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    unknown: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
    qualified:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    not_qualified:
      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    review_required:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    unreviewed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${colors[value] ?? colors.unknown}`}
    >
      {value.replace(/_/g, " ")}
    </span>
  );
}
function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

function formatMoney(value: number | null, rental: boolean) {
  if (value === null) return "Not available";
  return `${rental ? "R" : "R"}${Number(value).toLocaleString()}${rental ? " / month" : ""}`;
}

export default function Discovery() {
  const navigate = useNavigate();
  const canViewOperationalDiscoveryMetadata = ["owner", "admin"].includes(getCurrentUserRole() ?? "");
  const [items, setItems] = useState<Opportunity[]>([]);
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [sources, setSources] = useState<Source[]>([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [selected, setSelected] = useState<Opportunity | null>(null);
  const [events, setEvents] = useState<DiscoveryEvent[]>([]);
  const [reason, setReason] = useState("");
  const [contactDetails, setContactDetails] = useState({ name: "", phone: "", email: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [promotionMessage, setPromotionMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateFilter(name: string, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function loadOpportunities() {
    setLoading(true);
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== ""),
    );
    api
      .get<{ items: Opportunity[]; metrics: Record<string, number> }>(
        "/discovery/opportunities",
        { params },
      )
      .then((response) => {
        setItems(response.data.items);
        setMetrics(response.data.metrics);
        setError(null);
      })
      .catch(() => setError("Could not load discovery opportunities."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!canViewOperationalDiscoveryMetadata) return;
    api
      .get<Source[]>("/sources/")
      .then((response) => setSources(response.data))
      .catch(() => setSources([]));
    api
      .get<DiscoveryEvent[]>("/discovery/events")
      .then((response) => setEvents(response.data))
      .catch(() => setEvents([]));
  }, []);

  useEffect(loadOpportunities, [filters]);

  async function review(
    status: QualificationStatus,
    classification: Classification = selected?.classification ?? "unknown",
  ) {
    if (!selected) return;
    setSaving(true);
    try {
      const response = await api.patch<Opportunity>(
        `/discovery/opportunities/${selected.id}/review`,
        {
          classification,
          qualification_status: status,
          reason: reason.trim() || undefined,
        },
      );
      setSelected(response.data);
      setReason("");
      loadOpportunities();
    } catch {
      setError("Could not save the discovery review.");
    } finally {
      setSaving(false);
    }
  }

  async function promote(createTask = false) {
    if (!selected) return;
    setSaving(true);
    setPromotionMessage(null);
    try {
      const response = await api.post<{
        lead_id: string;
        lead_status: string;
        contact_created: boolean;
        lead_created: boolean;
        task_created: boolean;
        message: string;
      }>(`/discovery/opportunities/${selected.id}/promote`, {
        create_task: createTask,
      });
      setPromotionMessage(
        `${response.data.message} ${response.data.lead_created ? `Lead created - ${response.data.lead_status}.` : `Existing CRM lead is ${response.data.lead_status}.`}`,
      );
      setSelected((current) =>
        current
          ? {
              ...current,
              crm_status: "promoted",
              promotion_eligible: false,
              promotion_block_reason: null,
              lead_id: response.data.lead_id,
              lead_status: response.data.lead_status,
            }
          : current,
      );
      loadOpportunities();
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          "Could not promote this opportunity to CRM.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveContactDetails() {
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.patch<Opportunity>(
        `/discovery/opportunities/${selected.id}/contact`,
        contactDetails,
      );
      setSelected(response.data);
      loadOpportunities();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not save contact details.");
    } finally {
      setSaving(false);
    }
  }

  function resetFilters() {
    setFilters(emptyFilters);
  }

  const metricCards = [
    ["New Opportunities", metrics.new ?? 0],
    ["Seller Opportunities", metrics.seller ?? 0],
    ["Landlord Opportunities", metrics.landlord ?? 0],
    ["Needs Review", metrics.review_required ?? 0],
    ["Qualified", metrics.qualified ?? 0],
    ["Rejected", metrics.rejected ?? 0],
  ];

  return (
    <div className="space-y-6">
      <div className="nc-page-header">
        <div>
          <div className="nc-eyebrow">Lead intelligence</div>
          <h1 className="nc-page-title">Discovery</h1>
          <p className="nc-page-subtitle">
            Review property opportunities before they enter the CRM.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {metricCards.map(([label, value]) => (
          <div
            key={label}
            className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900"
          >
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {label}
            </div>
            <div className="mt-1 text-xl font-semibold text-gray-900 dark:text-white">
              {value}
            </div>
          </div>
        ))}
      </div>

      <div className="nc-surface p-4">
        <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-5">
          <input
            value={filters.q}
            onChange={(e) => updateFilter("q", e.target.value)}
            placeholder="Search address, suburb, source ID..."
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700 md:col-span-2"
          />
          <select
            value={filters.classification}
            onChange={(e) => updateFilter("classification", e.target.value)}
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          >
            <option value="">All opportunity types</option>
            <option value="seller">Seller</option>
            <option value="landlord">Landlord</option>
            <option value="unknown">Unknown</option>
          </select>
          <select
            aria-label="Listed by"
            value={filters.listed_by}
            onChange={(e) => updateFilter("listed_by", e.target.value)}
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          >
            <option value="">Listed by: All</option>
            <option value="owner">Listed by Owner</option>
            <option value="agent_agency">Agent/Agency</option>
            <option value="unknown">Unknown</option>
          </select>
          <select
            value={filters.listing_type}
            onChange={(e) => updateFilter("listing_type", e.target.value)}
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          >
            <option value="">All listing types</option>
            <option value="sale">Sale</option>
            <option value="rent">Rental</option>
          </select>
          <select
            value={filters.qualification_status}
            onChange={(e) =>
              updateFilter("qualification_status", e.target.value)
            }
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          >
            <option value="">All qualification states</option>
            <option value="unreviewed">Unreviewed</option>
            <option value="review_required">Review Required</option>
            <option value="qualified">Qualified</option>
            <option value="not_qualified">Rejected</option>
          </select>
          <input
            value={filters.property_type}
            onChange={(e) => updateFilter("property_type", e.target.value)}
            placeholder="Property type"
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          />
          <input
            value={filters.suburb}
            onChange={(e) => updateFilter("suburb", e.target.value)}
            placeholder="Suburb"
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          />
          {canViewOperationalDiscoveryMetadata && <select
            value={filters.source_id}
            onChange={(e) => updateFilter("source_id", e.target.value)}
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          >
            <option value="">All sources</option>
            {sources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name}
              </option>
            ))}
          </select>}
          <input
            value={filters.listing_status}
            onChange={(e) => updateFilter("listing_status", e.target.value)}
            placeholder="Listing status"
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          />
          <input
            type="number"
            value={filters.min_price}
            onChange={(e) => updateFilter("min_price", e.target.value)}
            placeholder="Min price"
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          />
          <input
            type="number"
            value={filters.max_price}
            onChange={(e) => updateFilter("max_price", e.target.value)}
            placeholder="Max price"
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          />
          <input
            type="number"
            value={filters.min_score}
            onChange={(e) => updateFilter("min_score", e.target.value)}
            placeholder="Min score"
            className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
          />
          <button
            onClick={resetFilters}
            className="rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Reset filters
          </button>
        </div>
      </div>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
          {error}
        </p>
      )}
      {loading ? (
        <p className="text-sm text-gray-400">
          Loading discovery opportunities...
        </p>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 px-6 py-12 text-center text-sm text-gray-400 dark:border-gray-700">
          No discovery opportunities match these filters.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
          <table className="min-w-[980px] w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 dark:bg-gray-900 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3 text-left">Property</th>
                <th className="px-4 py-3 text-left">Opportunity</th>
                <th className="px-4 py-3 text-left">Listing</th>
                <th className="px-4 py-3 text-left">Discovery</th>
                <th className="px-4 py-3 text-left">Source</th>
                <th className="px-4 py-3 text-left">Contact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => {
                    setSelected(item);
                    setReason(item.qualification_reason ?? "");
                    setContactDetails({
                      name: item.observation?.contact_name ?? "",
                      phone: item.observation?.contact_phone ?? "",
                      email: item.observation?.contact_email ?? "",
                    });
                  }}
                  className="cursor-pointer bg-white hover:bg-gray-50 dark:bg-gray-950 dark:hover:bg-gray-900"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {item.property.address ?? "Address unavailable"}
                    </div>
                    <div className="text-xs text-gray-500">
                      {[
                        item.property.suburb,
                        item.property.city,
                        item.property.province,
                      ]
                        .filter(Boolean)
                        .join(", ") || "Location unavailable"}
                    </div>
                    <div className="text-xs text-gray-400">
                      {item.property.property_type ??
                        "Property type unavailable"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="mb-2">
                      <Badge value={item.classification} />
                    </div>
                    <Badge value={item.qualification_status} />
                    {item.property.seller_type && (
                      <div className="mt-2 text-xs text-gray-500">
                        {item.property.seller_type === "owner"
                          ? "Listed by owner"
                          : item.property.seller_type}
                      </div>
                    )}
                    {item.duplicate && (
                      <div className="mt-2 text-xs font-medium text-orange-600">
                        {item.duplicate.match_type.replace(/_/g, " ")}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      {formatMoney(
                        item.property.listing_type === "rent"
                          ? item.property.monthly_rental
                          : item.property.asking_price,
                        item.property.listing_type === "rent",
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {item.property.listing_status}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold">
                      {item.opportunity_score}{" "}
                      <span className="text-xs text-gray-500">
                        {item.score_band}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {item.data_confidence} confidence ·{" "}
                      {formatDate(item.observation?.last_seen_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      {canViewOperationalDiscoveryMetadata
                        ? sources.find((source) => source.id === item.observation?.source_id)?.name ?? "Source unavailable"
                        : item.observation?.source_type ?? "Source unavailable"}
                    </div>
                    <div className="text-xs text-gray-500">
                      {item.observation?.source_listing_id ?? "No source ID"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {item.observation?.contact_name ?? "Not available"}
                    <div className="text-xs text-gray-500">
                      {item.observation?.contact_confidence ?? "unknown"}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div
          className="fixed inset-0 z-20 flex justify-end bg-black/30"
          onClick={() => setSelected(null)}
        >
          <section
            onClick={(event) => event.stopPropagation()}
            className="h-full w-full max-w-2xl overflow-y-auto bg-white p-6 shadow-xl dark:bg-gray-950"
          >
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Discovery review
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  {selected.property.address ?? "Address unavailable"}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="rounded-md px-2 py-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Close detail"
              >
                Close
              </button>
            </div>
            <div className="mb-6 flex flex-wrap gap-2">
              <Badge value={selected.classification} />
              <Badge value={selected.qualification_status} />
              <Badge value={selected.crm_status} />
              {selected.duplicate && (
                <Badge value={selected.duplicate.match_type} />
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Property information
                </h3>
                <dl className="space-y-1 text-sm">
                  <div>
                    <dt className="inline text-gray-500">Type: </dt>
                    <dd className="inline">
                      {selected.property.property_type ?? "Not available"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Listing party: </dt>
                    <dd className="inline">
                      {selected.property.seller_type === "owner"
                        ? "Listed by owner"
                        : (selected.property.seller_type ?? "Unknown")}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Location: </dt>
                    <dd className="inline">
                      {[
                        selected.property.address,
                        selected.property.suburb,
                        selected.property.city,
                        selected.property.province,
                      ]
                        .filter(Boolean)
                        .join(", ") || "Not available"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">
                      Beds/Baths/Garages:{" "}
                    </dt>
                    <dd className="inline">
                      {[
                        selected.property.bedrooms,
                        selected.property.bathrooms,
                        selected.property.garages,
                      ]
                        .map((value) => value ?? "-")
                        .join(" / ")}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Price: </dt>
                    <dd className="inline">
                      {formatMoney(
                        selected.property.listing_type === "rent"
                          ? selected.property.monthly_rental
                          : selected.property.asking_price,
                        selected.property.listing_type === "rent",
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Status: </dt>
                    <dd className="inline">
                      {selected.property.listing_status}
                    </dd>
                  </div>
                </dl>
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Discovery information
                </h3>
                <dl className="space-y-1 text-sm">
                  <div>
                    <dt className="inline text-gray-500">
                      Opportunity score:{" "}
                    </dt>
                    <dd className="inline font-semibold">
                      {selected.opportunity_score} ({selected.score_band})
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Property score: </dt>
                    <dd className="inline">{selected.property.lead_score}</dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Confidence: </dt>
                    <dd className="inline">{selected.data_confidence}</dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Evidence: </dt>
                    <dd className="inline">
                      {selected.intelligence_reasons.length
                        ? selected.intelligence_reasons.join(", ")
                        : "No intelligence signals recorded"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Next action: </dt>
                    <dd className="inline">
                      {selected.recommended_action ?? "Review source evidence"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Lifecycle: </dt>
                    <dd className="inline">
                      {selected.observation?.lifecycle_status ??
                        "Not available"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Source: </dt>
                    <dd className="inline">
                      {canViewOperationalDiscoveryMetadata
                        ? sources.find((source) => source.id === selected.observation?.source_id)?.name ?? "Not available"
                        : selected.observation?.source_type ?? "Not available"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Source ID: </dt>
                    <dd className="inline">
                      {selected.observation?.source_listing_id ??
                        "Not available"}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">First seen: </dt>
                    <dd className="inline">
                      {formatDate(selected.observation?.first_seen_at)}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline text-gray-500">Last seen: </dt>
                    <dd className="inline">
                      {formatDate(selected.observation?.last_seen_at)}
                    </dd>
                  </div>
                </dl>
                <div className="mt-4">
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Historical signals
                  </h4>
                  {selected.historical_signals.length ? (
                    <ul className="space-y-2 text-sm">
                      {selected.historical_signals.map((signal) => (
                        <li
                          key={`${signal.signal_type}-${signal.detected_at}-${signal.evidence}`}
                          className="border-l-2 border-brand-300 pl-3"
                        >
                          <div className="font-medium">
                            {signal.signal_type.replace(/_/g, " ")}{" "}
                            <span className="text-xs text-gray-500">
                              {signal.severity} · {signal.confidence}
                            </span>
                          </div>
                          <div className="text-gray-600 dark:text-gray-400">
                            {signal.evidence}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">
                      No historical signals recorded.
                    </p>
                  )}
                </div>
              </div>
            </div>
            <div className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="font-semibold text-slate-900 dark:text-white">
                {selected.crm_status === "promoted"
                  ? `Promoted to CRM${selected.lead_status ? ` - lead is ${selected.lead_status}.` : "."}`
                  : selected.promotion_eligible
                    ? "CRM promotion eligible"
                    : "CRM promotion blocked"}
              </div>
              {selected.promotion_block_reason && (
                <p className="mt-1 text-slate-500 dark:text-slate-400">
                  {selected.promotion_block_reason}
                </p>
              )}
              {selected.lead_id && (
                <button
                  type="button"
                  onClick={() => navigate(`/leads/${selected.lead_id}`)}
                  className="mt-3 rounded-md bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  Open CRM Lead
                </button>
              )}
            </div>
            <div className="mt-4 rounded-lg border border-slate-200 p-4 text-sm dark:border-slate-800">
              <div className="font-semibold text-slate-900 dark:text-white">Original listing</div>
              {selected.observation?.canonical_url ? (
                <a
                  href={selected.observation.canonical_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block font-medium text-brand-600 hover:underline dark:text-brand-500"
                >
                  View Original Listing
                </a>
              ) : (
                <p className="mt-1 text-gray-500">Original listing URL unavailable</p>
              )}
            </div>
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Contact information
              </h3>
              <dl className="grid gap-1 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-gray-500">Name</dt>
                  <dd>
                    {selected.observation?.contact_name ?? "Not available"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Confidence</dt>
                  <dd>
                    {selected.observation?.contact_confidence ?? "unknown"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Phone</dt>
                  <dd>
                    {selected.observation?.contact_phone ?? "Not available"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Email</dt>
                  <dd>
                    {selected.observation?.contact_email ?? "Not available"}
                  </dd>
                </div>
              </dl>
              <div className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
                <div className="font-semibold">Contact availability</div>
                {selected.observation?.contact_availability === "portal_mediated" ? (
                  <div>Portal-mediated: {selected.observation.portal_contact_methods.join(", ")}</div>
                ) : selected.observation?.contact_availability === "direct" ? (
                  <div>Direct contact details are available.</div>
                ) : (
                  <div>No contact information is available.</div>
                )}
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <input aria-label="Contact name" value={contactDetails.name} onChange={(event) => setContactDetails({ ...contactDetails, name: event.target.value })} placeholder="Contact name" className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700" />
                <input aria-label="Contact phone" value={contactDetails.phone} onChange={(event) => setContactDetails({ ...contactDetails, phone: event.target.value })} placeholder="Phone" className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700" />
                <input aria-label="Contact email" value={contactDetails.email} onChange={(event) => setContactDetails({ ...contactDetails, email: event.target.value })} placeholder="Email" className="rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700" />
              </div>
              <button disabled={saving} onClick={saveContactDetails} className="mt-3 rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300">
                Save contact details
              </button>
            </div>
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Media
              </h3>
              <p className="text-sm text-gray-500">
                Media metadata is shown only when supplied by an approved
                source. No media is downloaded or republished.
              </p>
              <p className="mt-1 text-sm">
                {selected.observation?.media.length ?? 0} media references
                available
              </p>
            </div>
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Review decision
              </h3>
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={3}
                placeholder="Add a qualification or rejection reason"
                className="mb-3 w-full rounded-md border border-gray-300 bg-transparent px-3 py-2 text-sm dark:border-gray-700"
              />
              <div className="flex flex-wrap gap-2">
                <button
                  disabled={saving}
                  onClick={() => review("qualified", "seller")}
                  className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  Qualify as Seller
                </button>
                <button
                  disabled={saving}
                  onClick={() => review("qualified", "landlord")}
                  className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  Qualify as Landlord
                </button>
                <button
                  disabled={saving}
                  onClick={() => review("not_qualified")}
                  className="rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Reject
                </button>
                <button
                  disabled={saving}
                  onClick={() => review("review_required")}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                  Review Later
                </button>
              </div>
              {selected.crm_status !== "promoted" && selected.qualification_status === "qualified" &&
                (selected.classification === "seller" ||
                  selected.classification === "landlord") && (
                  <div className="mt-4 border-t border-gray-200 pt-4 dark:border-gray-800">
                    <p className="mb-2 text-sm text-gray-500">
                      Promotion creates or matches a CRM contact and lead.
                      Creating a CRM task is a separate human-approved action.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        disabled={saving}
                        onClick={() => promote(false)}
                        className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                      >
                        Promote to CRM
                      </button>
                      <button
                        disabled={saving}
                        onClick={() => promote(true)}
                        className="rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                      >
                        Qualify &amp; create task
                      </button>
                    </div>
                    {promotionMessage && (
                      <p className="mt-2 text-sm text-green-700 dark:text-green-400">
                        {promotionMessage}
                      </p>
                    )}
                  </div>
                )}
            </div>
            {canViewOperationalDiscoveryMetadata && <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                Discovery events
              </h3>
              {events
                .filter((event) => event.property_id === selected.property_id)
                .slice(0, 10)
                .map((event) => (
                  <div
                    key={event.id}
                    className="border-l-2 border-brand-300 py-1 pl-3 text-sm"
                  >
                    <div>{event.event_type.replace(/_/g, " ")}</div>
                    <div className="text-xs text-gray-500">
                      {formatDate(event.created_at)}
                    </div>
                  </div>
                ))}
              {events.filter(
                (event) => event.property_id === selected.property_id,
              ).length === 0 && (
                <p className="text-sm text-gray-500">No events recorded.</p>
              )}
            </div>}
          </section>
        </div>
      )}
    </div>
  );
}


