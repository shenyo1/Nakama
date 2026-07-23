"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PUBLIC_API_BASE } from "@/lib/api";

const DEFAULT_PREFS = {
  theme: "dark",
  default_kind: "comic",
  default_source: "",
  items_per_page: 24,
  show_nsfw: false,
  email_notifications: true,
  language: "en",
  auto_refresh_enabled: true,
  auto_refresh_seconds: 30,
};

interface Prefs {
  theme?: string;
  default_kind?: string;
  default_source?: string;
  items_per_page?: number;
  show_nsfw?: boolean;
  email_notifications?: boolean;
  language?: string;
  auto_refresh_enabled?: boolean;
  auto_refresh_seconds?: number;
  [key: string]: unknown;
}

export default function PreferencesPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [prefs, setPrefs] = useState<Prefs>(DEFAULT_PREFS);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    ok: boolean;
    text: string;
  } | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("nakama_token");
    if (!token) {
      router.replace("/login?redirect=/preferences");
      return;
    }
    fetch(`${PUBLIC_API_BASE}/preferences`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok && d.data) {
          setPrefs({ ...DEFAULT_PREFS, ...(d.data.payload || {}) });
          setUpdatedAt(d.data.updated_at || null);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [router]);

  function update<K extends keyof Prefs>(key: K, value: Prefs[K]) {
    setPrefs((p) => ({ ...p, [key]: value }));
  }

  async function save() {
    const token = localStorage.getItem("nakama_token");
    if (!token) return;
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/preferences`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ payload: prefs }),
      });
      const body = await res.json();
      if (body.ok) {
        setMessage({ ok: true, text: "Preferences saved." });
        setUpdatedAt(body.data?.updated_at || null);
      } else {
        setMessage({ ok: false, text: body.detail || body.error || "Save failed" });
      }
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Network error" });
    } finally {
      setSaving(false);
    }
  }

  async function reset() {
    if (!confirm("Reset all preferences to defaults?")) return;
    const token = localStorage.getItem("nakama_token");
    if (!token) return;
    setResetting(true);
    setMessage(null);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/preferences`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await res.json();
      if (body.ok) {
        setPrefs(DEFAULT_PREFS);
        setMessage({ ok: true, text: "Preferences reset to defaults." });
      } else {
        setMessage({ ok: false, text: body.detail || "Reset failed" });
      }
    } catch (e) {
      setMessage({ ok: false, text: e instanceof Error ? e.message : "Network error" });
    } finally {
      setResetting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 rounded bg-ink-800 animate-pulse" />
        <div className="h-64 w-full rounded bg-ink-800/50 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8 max-w-2xl mx-auto">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Preferences</h1>
        <p className="text-sm text-ink-400">
          Customize your Nakama experience. Preferences are saved per account and
          sync across devices.
        </p>
        {updatedAt && (
          <p className="text-xs text-ink-500">
            Last updated: {new Date(updatedAt).toLocaleString()}
          </p>
        )}
      </header>

      {/* Display */}
      <section className="card space-y-4">
        <h2 className="font-semibold text-sm sm:text-base">Display</h2>
        <div className="grid gap-3 sm:gap-4 sm:grid-cols-2">
          <Field label="Theme">
            <select
              className="input"
              value={prefs.theme}
              onChange={(e) => update("theme", e.target.value)}
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="system">System</option>
            </select>
          </Field>
          <Field label="Items per page">
            <input
              type="number"
              className="input"
              min={6}
              max={100}
              value={prefs.items_per_page}
              onChange={(e) =>
                update("items_per_page", parseInt(e.target.value, 10) || 24)
              }
            />
          </Field>
        </div>
      </section>

      {/* Browse defaults */}
      <section className="card space-y-4">
        <h2 className="font-semibold text-sm sm:text-base">Browse Defaults</h2>
        <div className="grid gap-3 sm:gap-4 sm:grid-cols-2">
          <Field label="Default content type">
            <select
              className="input"
              value={prefs.default_kind}
              onChange={(e) => update("default_kind", e.target.value)}
            >
              <option value="anime">Anime</option>
              <option value="comic">Comic</option>
              <option value="novel">Novel</option>
            </select>
          </Field>
          <Field label="Default source (optional)">
            <input
              type="text"
              className="input"
              placeholder="e.g. komiku, otakudesu, sakuranovel"
              value={prefs.default_source}
              onChange={(e) => update("default_source", e.target.value)}
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={prefs.show_nsfw}
            onChange={(e) => update("show_nsfw", e.target.checked)}
            className="h-4 w-4"
          />
          <span>Show NSFW / adult content sources</span>
        </label>
      </section>

      {/* Notifications */}
      <section className="card space-y-4">
        <h2 className="font-semibold text-sm sm:text-base">Notifications</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={prefs.email_notifications}
            onChange={(e) => update("email_notifications", e.target.checked)}
            className="h-4 w-4"
          />
          <span>Email notifications (password reset confirmations, alerts)</span>
        </label>
      </section>

      {/* Dashboard auto-refresh */}
      <section className="card space-y-4">
        <h2 className="font-semibold text-sm sm:text-base">Dashboard</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={prefs.auto_refresh_enabled}
            onChange={(e) =>
              update("auto_refresh_enabled", e.target.checked)
            }
            className="h-4 w-4"
          />
          <span>Auto-refresh source health</span>
        </label>
        {prefs.auto_refresh_enabled && (
          <Field label="Refresh interval (seconds)">
            <input
              type="number"
              className="input"
              min={10}
              max={300}
              value={prefs.auto_refresh_seconds}
              onChange={(e) =>
                update(
                  "auto_refresh_seconds",
                  parseInt(e.target.value, 10) || 30
                )
              }
            />
          </Field>
        )}
      </section>

      {/* Language */}
      <section className="card space-y-4">
        <h2 className="font-semibold text-sm sm:text-base">Language</h2>
        <Field label="Interface language">
          <select
            className="input"
            value={prefs.language}
            onChange={(e) => update("language", e.target.value)}
          >
            <option value="en">English</option>
            <option value="id">Bahasa Indonesia</option>
          </select>
        </Field>
      </section>

      {/* Actions */}
      <div className="flex flex-wrap gap-2 sm:gap-3">
        <button
          onClick={save}
          disabled={saving || resetting}
          className="btn-primary"
        >
          {saving ? "Saving…" : "Save preferences"}
        </button>
        <button
          onClick={reset}
          disabled={saving || resetting}
          className="btn-ghost"
        >
          {resetting ? "Resetting…" : "Reset to defaults"}
        </button>
        <Link href="/dashboard" className="btn-ghost">
          Back to dashboard
        </Link>
      </div>

      {message && (
        <div
          className={`text-sm ${message.ok ? "text-jade-400" : "text-rose-400"}`}
          role="status"
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-ink-400">{label}</span>
      {children}
    </label>
  );
}
