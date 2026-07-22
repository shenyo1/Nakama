"use client";

import { useState } from "react";
import { PUBLIC_API_BASE } from "../../lib/api";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const body = await res.json();
      if (body.ok && body.data?.access_token) {
        localStorage.setItem("nakama_token", body.data.access_token);
        localStorage.setItem("nakama_user", JSON.stringify(body.data.user || {}));
        setResult({ ok: true, message: "Login successful" });
        setTimeout(() => window.location.href = "/", 1000);
      } else {
        setResult({ ok: false, message: body.detail || body.error || "Login failed" });
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
        <h1 className="text-2xl font-bold sm:text-3xl">Login</h1>
        <p className="text-sm text-ink-400">Sign in to sync bookmarks and preferences.</p>
      </header>

      <form onSubmit={handleSubmit} className="card space-y-3">
        <label className="block text-sm">
          <span className="mb-1 block text-ink-400">Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
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
            className="input"
            placeholder="password"
          />
        </label>
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>

      {result ? (
        <div className={`card text-sm ${result.ok ? "text-neon-400" : "text-sakura-300"}`}>
          {result.message}
        </div>
      ) : null}

      <p className="text-center text-xs text-ink-500">
        Don&apos;t have an account?{" "}
        <a href="/register" className="text-sakura-400 hover:underline">Register</a>
      </p>
    </div>
  );
}
