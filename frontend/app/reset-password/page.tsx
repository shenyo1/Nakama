"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PUBLIC_API_BASE } from "../../lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  useEffect(() => {
    if (!token) setResult({ ok: false, message: "Missing token. Use the link from your reset email." });
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setResult({ ok: false, message: "Password must be at least 8 characters." });
      return;
    }
    if (password !== confirm) {
      setResult({ ok: false, message: "Passwords do not match." });
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/auth/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      const body = await res.json();
      if (res.ok && body.ok) {
        setResult({ ok: true, message: "Password reset. Redirecting to login…" });
        setTimeout(() => router.push("/login"), 1500);
      } else {
        setResult({ ok: false, message: body.detail || body.error || "Reset failed" });
      }
    } catch (err) {
      setResult({ ok: false, message: err instanceof Error ? err.message : "Network error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-sm mx-auto">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Reset password</h1>
        <p className="text-sm text-ink-400">Choose a new password for your account.</p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-3">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">New password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="input"
            placeholder="≥ 8 characters"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">Confirm new password</span>
          <input
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
            className="input"
          />
        </label>

        <button type="submit" disabled={loading || !token} className="btn-primary w-full">
          {loading ? "Resetting…" : "Reset password"}
        </button>

        {result && (
          <div className={`text-sm ${result.ok ? "text-jade-400" : "text-rose-400"}`}>
            {result.message}
          </div>
        )}
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="card max-w-sm mx-auto">Loading…</div>}>
      <ResetForm />
    </Suspense>
  );
}