import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, register } from "@/lib/api";

export default function Login() {
  const [isRegistering, setIsRegistering] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      if (isRegistering) {
        await register(email, password, fullName);

        setMessage("Account created successfully. You can now sign in.");
        setIsRegistering(false);
        setPassword("");
        setShowPassword(false);
      } else {
        await login(email, password);
        navigate("/");
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail;

      if (isRegistering) {
        setError(detail || "Unable to create account");
      } else {
        setError(detail || "Invalid email or password");
      }
    } finally {
      setLoading(false);
    }
  }

  function switchMode() {
    setIsRegistering((value) => !value);
    setError(null);
    setMessage(null);
    setPassword("");
    setShowPassword(false);
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
          {isRegistering
            ? "Create your NexaCore account"
            : "Sign in to your account"}
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

        {isRegistering && (
          <>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Full name
            </label>

            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="mb-4 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
              placeholder="Your name"
            />
          </>
        )}

        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Email
        </label>

        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-4 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
          placeholder="you@example.com"
          required
        />

        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Password
        </label>

        <div className="relative mb-6">
          <input
            type={showPassword ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-transparent px-3 py-2 pr-11 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
            placeholder="Enter your password"
            required
          />

          <button
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            title={showPassword ? "Hide password" : "Show password"}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
          >
            {showPassword ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-5 w-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 4.2A10.7 10.7 0 0112 4c5 0 8.7 3.3 10 8a10.8 10.8 0 01-2.1 3.9M6.6 6.6C4.8 7.9 3.5 9.7 2 12c1.3 4.7 5 8 10 8 1.5 0 2.8-.3 4-.8"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-5 w-5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"
                />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        </div>

        {!isRegistering && (
          <div className="-mt-4 mb-6 text-right text-sm">
            <Link
              to="/forgot-password"
              className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-500"
            >
              Forgot Password?
            </Link>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-brand-600 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {loading
            ? "Please wait..."
            : isRegistering
              ? "Create account"
              : "Sign in"}
        </button>

        <div className="mt-5 text-center text-sm text-gray-500 dark:text-gray-400">
          {isRegistering
            ? "Already have an account?"
            : "Don't have an account?"}{" "}
          <button
            type="button"
            onClick={switchMode}
            className="font-medium text-brand-600 hover:text-brand-700 dark:text-brand-500"
          >
            {isRegistering ? "Sign in" : "Create account"}
          </button>
        </div>
      </form>
    </div>
  );
}
