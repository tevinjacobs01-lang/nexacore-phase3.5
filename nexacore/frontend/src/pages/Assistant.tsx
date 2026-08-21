import { useState } from "react";
import { api } from "@/lib/api";

type Mode = "ask" | "prioritize";

export default function Assistant() {
  const [mode, setMode] = useState<Mode>("ask");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const suggestions = [
    "Show me all listings older than 90 days.",
    "Which properties should I call first today?",
    "Show all rentals above R12,000.",
  ];

  async function handleAsk(q: string) {
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const { data } = await api.post("/ai/ask", { question: q });
      setAnswer(data.answer);
    } catch (err: any) {
      setError(
        err?.response?.status === 503
          ? "AI assistant isn't configured yet — add ANTHROPIC_API_KEY to your .env."
          : "Something went wrong asking the assistant."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handlePrioritize() {
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const { data } = await api.post("/ai/prioritize", {});
      setAnswer(data.answer);
    } catch (err: any) {
      setError(
        err?.response?.status === 503
          ? "AI assistant isn't configured yet — add ANTHROPIC_API_KEY to your .env."
          : "Something went wrong prioritizing listings."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
        AI Assistant
      </h2>

      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setMode("ask")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium ${
            mode === "ask"
              ? "bg-brand-600 text-white"
              : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
          }`}
        >
          Ask a question
        </button>
        <button
          onClick={() => {
            setMode("prioritize");
            handlePrioritize();
          }}
          className={`rounded-md px-3 py-1.5 text-sm font-medium ${
            mode === "prioritize"
              ? "bg-brand-600 text-white"
              : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
          }`}
        >
          Who should I call today?
        </button>
      </div>

      {mode === "ask" && (
        <>
          <div className="mb-3 flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && question && handleAsk(question)}
              placeholder="Ask about your listings…"
              className="flex-1 rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 text-sm"
            />
            <button
              onClick={() => handleAsk(question)}
              disabled={!question || loading}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Ask
            </button>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuestion(s);
                  handleAsk(s);
                }}
                className="rounded-full border border-gray-300 dark:border-gray-700 px-3 py-1 text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                {s}
              </button>
            ))}
          </div>
        </>
      )}

      {loading && <p className="text-sm text-gray-400">Thinking…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {answer && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">
          {answer}
        </div>
      )}
    </div>
  );
}
