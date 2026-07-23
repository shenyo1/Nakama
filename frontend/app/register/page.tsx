"use client";

import { useId, useRef, useState } from "react";
import { PUBLIC_API_BASE } from "../../lib/api";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    ok: boolean;
    message: string;
    link?: string;
  } | null>(null);

  // Unique IDs so labels and aria-describedby work for screen readers.
  const userId = useId();
  const passId = useId();
  const emailId = useId();
  const statusId = useId();
  const statusRef = useRef<HTMLDivElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setResult({ ok: false, message: "Password must be at least 8 characters." });
      statusRef.current?.focus();
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const body: Record<string, string> = { username, password };
      if (email) body.email = email;
      const res = await fetch(`${PUBLIC_API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.ok) {
        const link = data.data?.email_confirmation?.confirmation_link as
          | string
          | undefined;
        const msg = email
          ? link
            ? "Account created. Confirmation link generated (shown below — production would email it)."
            : "Account created. Check your inbox to confirm your email."
          : "Account created. You can now login.";
        setResult({ ok: true, message: msg, link });
        setTimeout(() => (window.location.href = "/login"), 2000);
      } else {
        setResult({
          ok: false,
          message: data.detail || data.error || "Registration failed",
        });
      }
    } catch (err) {
      setResult({
        ok: false,
        message: err instanceof Error ? err.message : "Network error",
      });
    } finally {
      setLoading(false);
      statusRef.current?.focus();
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-sm mx-auto">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Register</h1>
        <p className="text-sm text-ink-400">
          Create an account for bookmarks and preferences.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-3" noValidate>
        <label className="block text-sm" htmlFor={userId}>
          <span className="mb-1 block text-ink-400">Username</span>
          <input
            id={userId}
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            autoComplete="username"
            aria-required="true"
            aria-describedby={`${userId}-help`}
            className="input"
            placeholder="username"
          />
          <span id={`${userId}-help`} className="sr-only">
            At least 3 characters
          </span>
        </label>
        <label className="block text-sm" htmlFor={passId}>
          <span className="mb-1 block text-ink-400">Password</span>
          <input
            id={passId}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            aria-required="true"
            aria-describedby={`${passId}-help`}
            className="input"
            placeholder="≥ 8 characters"
          />
          <span id={`${passId}-help`} className="sr-only">
            At least 8 characters
          </span>
        </label>
        <label className="block text-sm" htmlFor={emailId}>
          <span className="mb-1 block text-ink-400">
            Email <span className="text-ink-500">(optional, for password reset)</span>
          </span>
          <input
            id={emailId}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            className="input"
            placeholder="you@example.com"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full"
          aria-busy={loading}
        >
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>

      {result ? (
        <div
          ref={statusRef}
          id={statusId}
          tabIndex={-1}
          role={result.ok ? "status" : "alert"}
          aria-live={result.ok ? "polite" : "assertive"}
          className={`card text-sm focus:outline-none focus:ring-2 ${
            result.ok ? "text-jade-400" : "text-rose-400"
          }`}
        >
          {result.message}
          {result.link && (
            <div className="mt-2 break-all">
              <a href={result.link} className="text-sakura-400 underline">
                {result.link}
              </a>
            </div>
          )}
        </div>
      ) : null}

      <p className="text-center text-xs text-ink-500">
        Already have an account?{" "}
        <a href="/login" className="text-sakura-400 hover:underline">
          Login
        </a>
      </p>
    </div>
  );
}
