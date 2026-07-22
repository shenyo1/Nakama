"use client";

import { useState } from "react";
import { PUBLIC_API_BASE } from "../../lib/api";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const body = await res.json();
      if (body.ok) {
        setResult({ ok: true, message: "Account created. You can now login." });
        setTimeout(() => window.location.href = "/login", 1500);
      } else {
        setResult({ ok: false, message: body.detail || body.error || "Registration failed" });
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
        <h1 className="text-2xl font-bold sm:text-3xl">Register</h1>
        <p className="text-sm text-ink-400">Create an account for bookmarks and preferences.</p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-3">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            className="input"
            placeholder="username"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="input"
            placeholder="password"
          />
        </label>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Creating..." : "Create account"}
        </button>
      </form>

      {result ? (
        <div className={`card text-sm ${result.ok ? "text-neon-400" : "text-sakura-300"}`}>
          {result.message}
        </div>
      ) : null}

      <p className="text-center text-xs text-ink-500">
        Already have an account?{" "}
        <a href="/login" className="text-sakura-400 hover:underline">Login</a>
      </p>
    </div>
  );
}
