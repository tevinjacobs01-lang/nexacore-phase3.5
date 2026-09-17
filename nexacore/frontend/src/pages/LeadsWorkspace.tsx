import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, getCurrentUserRole } from "@/lib/api";

interface UnifiedLeadItem {
  type: "lead" | "opportunity";
  id: string;
  contact_name: string | null;
  property_address: string | null;
  property_suburb: string | null;
  source: string;
  source_key: string;
  status: string;
  classification?: string;
  lead_score: number;
  opportunity_score?: number;
  priority?: string;
  next_action: {
    action_type: string;
    action_label: string;
    urgency: string;
    due_at: string | null;
    reason: string;
  };
  workflow_action: string;
}

interface InboxResponse {
  items: UnifiedLeadItem[];
  total: number;
  metrics: {
    total_leads: number;
    awaiting_review: number;
  };
}

export default function LeadsWorkspace() {
  const navigate = useNavigate();

  const [items, setItems] = useState<UnifiedLeadItem[]>([]);
  const [metrics, setMetrics] = useState({
    total_leads: 0,
    awaiting_review: 0,
  });
  const [loading, setLoading] = useState(true);
  const [diagnostic, setDiagnostic] = useState("");
  const [role] = useState<string | null>(() => getCurrentUserRole());

  useEffect(() => {
    const loadItems = async () => {
      try {
        const response = await api.get<InboxResponse>("/leads/inbox");

        console.log("LEADS INBOX RESPONSE:", response.data);

        setDiagnostic(
          `API total=${response.data.total}, items=${response.data.items?.length ?? 0}`
        );

        setItems(response.data.items);
        setMetrics(response.data.metrics);
      } catch (error: any) {
        console.error("Failed to load leads inbox:", error);

        const status = error?.response?.status;
        const message =
          error?.response?.data?.detail ||
          error?.message ||
          "Unknown error";

        setDiagnostic(
          `API ERROR status=${status ?? "unknown"}, message=${message}`
        );

        setMetrics({
          total_leads: -1,
          awaiting_review: status ?? -1,
        });

        setItems([]);
      } finally {
        setLoading(false);
      }
    };

    loadItems();
  }, []);

  if (loading) {
    return <div className="p-6">Loading unified leads workspace...</div>;
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Unified Leads Workspace</h1>

        <p className="text-sm text-gray-600 mt-1">
          {metrics.total_leads} active leads · {metrics.awaiting_review} awaiting review
        </p>

        <p className="text-xs text-gray-500 mt-2">
          Diagnostic: {diagnostic}
        </p>

        <p className="text-xs text-gray-500 mt-1">
          Role: {role ?? "unknown"}
        </p>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No leads or opportunities available.
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((item) => (
            <div
              key={`${item.type}-${item.id}`}
              onClick={() => {
                if (item.type === "lead") {
                  navigate(`/leads/${item.id}`);
                } else {
                  navigate(`/discovery`);
                }
              }}
              className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-semibold">
                    {item.contact_name || "Unknown"}
                  </div>

                  <div className="text-sm text-gray-600">
                    {item.property_address}{" "}
                    {item.property_suburb &&
                      `, ${item.property_suburb}`}
                  </div>

                  <div className="text-sm mt-2">
                    <span className="inline-block px-2 py-1 bg-gray-100 rounded mr-2">
                      {item.source}
                    </span>

                    <span className="inline-block px-2 py-1 bg-gray-100 rounded">
                      {item.status}
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-semibold text-lg">
                    {item.lead_score}
                  </div>

                  <div className="text-xs text-gray-500">
                    {item.next_action.urgency}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}