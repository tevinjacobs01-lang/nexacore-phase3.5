import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import type { Lead } from "@/types/lead";
import { PIPELINE_STAGES } from "@/types/lead";

const PRIORITY_COLORS: Record<string, string> = {
  high: "border-l-4 border-red-500",
  medium: "border-l-4 border-amber-400",
  low: "border-l-4 border-gray-300",
};

export default function Leads() {
  const [pipeline, setPipeline] = useState<Record<string, Lead[]> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  function fetchPipeline() {
    api
      .get("/leads/pipeline")
      .then((res) => setPipeline(res.data))
      .catch(() => setError("Could not load the pipeline."));
  }

  useEffect(fetchPipeline, []);

  async function advanceStage(e: React.MouseEvent, lead: Lead, newStatus: string) {
    e.stopPropagation();
    await api.patch(`/leads/${lead.id}`, { status: newStatus });
    fetchPipeline();
  }

  if (error) return <p className="text-red-600">{error}</p>;
  if (!pipeline) return <p className="text-gray-400">Loading…</p>;

  const totalLeads = Object.values(pipeline).reduce((sum, leads) => sum + leads.length, 0);

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
        Lead Pipeline
      </h2>

      {totalLeads === 0 ? (
        <p className="text-sm text-gray-400">No leads yet. Create a lead from a property to get started.</p>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {PIPELINE_STAGES.map((stage, stageIdx) => {
            const leads = pipeline[stage.key] ?? [];
            const nextStage = PIPELINE_STAGES[stageIdx + 1];
            return (
              <div key={stage.key} className="w-56 shrink-0 rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    {stage.label}
                  </h3>
                  <span className="text-xs text-gray-400">{leads.length}</span>
                </div>
                <div className="space-y-2">
                  {leads.map((lead) => (
                    <div
                      key={lead.id}
                      onClick={() => navigate(`/leads/${lead.id}`)}
                      className={`cursor-pointer rounded-md bg-gray-50 dark:bg-gray-800 p-2 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 ${PRIORITY_COLORS[lead.priority]}`}
                    >
                      <div className="mb-1 text-gray-500 dark:text-gray-400">
                        Priority: {lead.priority}
                      </div>
                      {lead.next_follow_up && (
                        <div className="mb-1 text-gray-500 dark:text-gray-400">
                          Follow-up: {lead.next_follow_up}
                        </div>
                      )}
                      {nextStage && (
                        <button
                          onClick={(e) => advanceStage(e, lead, nextStage.key)}
                          className="text-brand-600 dark:text-brand-500 hover:underline"
                        >
                          Move to {nextStage.label} →
                        </button>
                      )}
                    </div>
                  ))}
                  {leads.length === 0 && <p className="text-xs text-gray-300 dark:text-gray-600">Empty</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
