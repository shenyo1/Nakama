"use client";

import { useState } from "react";

interface BookmarkButtonProps {
  contentType: "comic" | "anime" | "novel";
  contentId: string;
  source: string;
  title: string;
  thumbnail?: string;
}

const API_INTERNAL_URL = process.env.NEXT_PUBLIC_API_BASE || "https://api.mynakama.web.id";

export function BookmarkButton({
  contentType,
  contentId,
  source,
  title,
  thumbnail,
}: BookmarkButtonProps) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    const token = typeof window !== "undefined" ? localStorage.getItem("nakama_token") : null;
    if (!token) {
      setError("Login required to bookmark");
      setTimeout(() => setError(null), 3000);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API_INTERNAL_URL}/bookmarks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content_type: contentType,
          content_id: contentId,
          source,
          title,
          thumbnail,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      if (json.ok) {
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        setError(json.error || "Failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={saving}
      title={error || saved ? (saved ? "Saved!" : error!) : "Bookmark this"}
      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
        saved
          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
          : error
          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
          : "bg-sakura-500/20 text-sakura-300 border border-sakura-500/30 hover:bg-sakura-500/30"
      } disabled:opacity-50`}
    >
      {saving ? "…" : saved ? "✓ Saved" : error ? "!" : "♡ Bookmark"}
    </button>
  );
}
