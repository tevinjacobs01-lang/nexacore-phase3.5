import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LeadScoreRule } from "@/types/scoring";

const CONFIG_HINTS: Record<string, string> = {
  days_on_market_gt_30: "Threshold in days (e.g. 30)",
  days_on_market_gt_60: "Threshold in days (e.g. 60)",
  days_on_market_gt_90: "Threshold in days (e.g. 90)",
  preferred_suburb: "Comma-separated suburb names",
  price_range_match: "min,max — e.g. 800000,1500000",
  luxury_property: "Price threshold (e.g. 3000000)",
  recent_price_reduction: "Lookback window in days (e.g. 30)",
};

export default function Settings() {
  const [rules, setRules] = useState<LeadScoreRule[]>([]);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [recomputing, setRecomputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function fetchRules() {
    api
      .get<LeadScoreRule[]>("/scoring/rules")
      .then((res) => setRules(res.data))
      .catch(() => setError("Could not load rules. Admin access is required for this page."));
  }

  useEffect(fetchRules, []);

  async function updateRule(rule: LeadScoreRule, changes: Partial<LeadScoreRule>) {
    setSavingId(rule.id);
    try {
      const { data } = await api.patch<LeadScoreRule>(`/scoring/rules/${rule.id}`, changes);
      setRules((prev) => prev.map((r) => (r.id === rule.id ? data : r)));
    } catch {
      setError(`Failed to save "${rule.name}"`);
    } finally {
      setSavingId(null);
    }
  }

  async function handleRecomputeAll() {
    setRecomputing(true);
    try {
      await api.post("/scoring/recompute");
    } finally {
      setRecomputing(false);
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
          Lead Scoring Rules
        </h2>
        <button
          onClick={handleRecomputeAll}
          disabled={recomputing}
          className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {recomputing ? "Recomputing…" : "Recompute All Scores"}
        </button>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2 text-left">Rule</th>
              <th className="px-4 py-2 text-left">Points</th>
              <th className="px-4 py-2 text-left">Config</th>
              <th className="px-4 py-2 text-left">Active</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {rules.map((rule) => (
              <tr key={rule.id} className="bg-white dark:bg-gray-950">
                <td className="px-4 py-2">
                  <div className="font-medium text-gray-800 dark:text-gray-100">{rule.name}</div>
                  {CONFIG_HINTS[rule.rule_key] && (
                    <div className="text-xs text-gray-400">{CONFIG_HINTS[rule.rule_key]}</div>
                  )}
                </td>
                <td className="px-4 py-2">
                  <input
                    type="number"
                    defaultValue={rule.points}
                    onBlur={(e) => {
                      const points = Number(e.target.value);
                      if (points !== rule.points) updateRule(rule, { points });
                    }}
                    className="w-20 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1 text-sm"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="text"
                    defaultValue={rule.config ?? ""}
                    onBlur={(e) => {
                      const config = e.target.value;
                      if (config !== (rule.config ?? "")) updateRule(rule, { config });
                    }}
                    className="w-56 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-2 py-1 text-sm"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="checkbox"
                    checked={rule.is_active}
                    onChange={(e) => updateRule(rule, { is_active: e.target.checked })}
                  />
                  {savingId === rule.id && (
                    <span className="ml-2 text-xs text-gray-400">saving…</span>
                  )}
                </td>
              </tr>
            ))}
            {rules.length === 0 && !error && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  Loading rules…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-gray-400">
        Edits save automatically when you leave a field. Score changes apply on next
        import or when you hit "Recompute All Scores."
      </p>
    </div>
  );
}
