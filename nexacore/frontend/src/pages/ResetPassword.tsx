import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "@/lib/api";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [resetToken, setResetToken] = useState(searchParams.get("token") || "");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      const response = await resetPassword(resetToken, newPassword);
      setMessage(response.message);
      setNewPassword("");
      window.setTimeout(() => navigate("/login"), 1200);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Unable to reset password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-8 shadow-sm"
      >
        <h1 className="text-xl font-semibold text-brand-600 dark:text-brand-500 mb-2">
          NexaCore
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          Choose a new password
        </p>

        {error && (
          <p className="mb-4 rounded-md bg-red-50 dark:bg-red-950/30 px-3 py-2 text-sm text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
        {message && (
          <p className="mb-4 rounded-md bg-green-50 dark:bg-green-950/30 px-3 py-2 text-sm text-green-600 dark:text-green-400">
            {message}
          </p>
        )}

        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Reset token
        </label>
        <input
          type="text"
          value={resetToken}
          onChange={(event) => setResetToken(event.target.value)}
          className="mb-4 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
          placeholder="Paste your reset token"
          required
        />

        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          New password
        </label>
        <input
          type="password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          className="mb-6 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
          placeholder="Enter your new password"
          minLength={8}
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-brand-600 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading ? "Please wait..." : "Reset password"}
        </button>

        <Link
          to="/login"
          className="mt-5 block text-center text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-500"
        >
          Back to sign in
        </Link>
      </form>
    </div>
  );
}