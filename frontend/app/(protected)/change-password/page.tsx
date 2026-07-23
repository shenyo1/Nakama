"use client";

import { useState } from "react";
import Link from "next/link";
import { PUBLIC_API_BASE } from "@/lib/api";

export default function ChangePasswordPage() {
  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(
    null
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setResult(null);

    if (newPass.length < 8) {
      setResult({ ok: false, message: "New password must be at least 8 characters." });
      return;
    }
    if (newPass !== confirm) {
      setResult({ ok: false, message: "Passwords do not match." });
      return;
    }
    if (newPass === current) {
      setResult({
        ok: false,
        message: "New password must be different from current password.",
      });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem("nakama_token");
      if (!token) {
        setResult({ ok: false, message: "Not logged in." });
        return;
      }
      const res = await fetch(`${PUBLIC_API_BASE}/auth/change-password`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: current,
          new_password: newPass,
        }),
      });
      const body = await res.json();
      if (res.ok && body.ok) {
        setResult({
          ok: true,
          message:
            "Password changed. Please log in again with your new password.",
        });
        // Force logout so the user re-authenticates
        setTimeout(() => {
          localStorage.removeItem("nakama_token");
          localStorage.removeItem("nakama_user");
          window.location.href = "/login";
        }, 1500);
      } else {
        setResult({
          ok: false,
          message: body.detail || body.error || "Change failed",
        });
      }
    } catch (err) {
      setResult({
        ok: false,
        message: err instanceof Error ? err.message : "Network error",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-sm mx-auto">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Change password</h1>
        <p className="text-sm text-ink-400">
          Enter your current password and choose a new one (≥ 8 characters).
        </p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-3">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">Current password</span>
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            required
            autoComplete="current-password"
            className="input"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">New password</span>
          <input
            type="password"
            value={newPass}
            onChange={(e) => setNewPass(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
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
            autoComplete="new-password"
            className="input"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full"
          aria-busy={loading}
        >
          {loading ? "Changing…" : "Change password"}
        </button>

        {result && (
          <div
            className={`text-sm ${result.ok ? "text-jade-400" : "text-rose-400"}`}
            role="status"
            aria-live="polite"
          >
            {result.message}
          </div>
        )}

        <p className="text-xs text-ink-500">
          <Link href="/preferences" className="text-sakura-400 underline">
            Back to preferences
          </Link>
        </p>
      </form>
    </div>
  );
}
