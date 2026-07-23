"use client";

import { useState } from "react";
import { PUBLIC_API_BASE } from "../../lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string; link?: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/auth/forgot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const body = await res.json();
      // Always 200 to avoid user enumeration.
      const link = body.data?.reset?.reset_link as string | undefined;
      const msg = link
        ? "Reset link generated. Check the link below (in production this is emailed)."
        : "If an account exists for that email, a reset link has been sent.";
      setResult({ ok: true, message: msg, link });
    } catch (err) {
      setResult({ ok: false, message: err instanceof Error ? err.message : "Network error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-sm mx-auto">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Forgot password</h1>
        <p className="text-sm text-ink-400">
          Enter the email associated with your account. If it matches, we&apos;ll send a reset link.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-3">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input"
            placeholder="you@example.com"
          />
        </label>

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Sending…" : "Send reset link"}
        </button>

        {result && (
          <div className={`text-sm ${result.ok ? "text-jade-400" : "text-rose-400"}`}>
            {result.message}
            {result.link && (
              <div className="mt-2 break-all">
                <a href={result.link} className="text-sakura-400 underline">
                  {result.link}
                </a>
              </div>
            )}
          </div>
        )}

        <p className="text-xs text-ink-500">
          Remembered it?{" "}
          <a href="/login" className="text-sakura-400 underline">
            Back to login
          </a>
        </p>
      </form>
    </div>
  );
}