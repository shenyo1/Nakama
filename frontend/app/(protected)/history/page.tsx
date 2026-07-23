"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PUBLIC_API_BASE } from "@/lib/api";

interface HistoryEntry {
  id: number;
  source: string;
  content_id: string;
  content_type: "anime" | "comic" | "novel";
  chapter_id: string;
  read_at: string;
}

const KIND_LABELS: Record<string, { label: string; color: string }> = {
  anime: { label: "Anime", color: "bg-blue-500" },
  comic: { label: "Comic", color: "bg-sakura-500" },
  novel: { label: "Novel", color: "bg-emerald-500" },
};

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("nakama_token");
    if (!token) {
      setError("Login required to view history");
      setLoading(false);
      return;
    }
    fetch(`${PUBLIC_API_BASE}/history`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (Array.isArray(data)) {
          setEntries(data);
        } else if (data.data && Array.isArray(data.data)) {
          setEntries(data.data);
        } else {
          setEntries([]);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function buildHref(e: HistoryEntry): string {
    if (e.content_type === "comic") {
      return `/comic/${e.source}/chapter/${e.content_id}/${e.chapter_id}`;
    }
    if (e.content_type === "anime") {
      return `/anime/${e.source}/episode/${e.chapter_id}`;
    }
    return `/novel/${e.source}/chapter/${e.chapter_id}`;
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Continue Reading</h1>
        <p className="text-sm text-ink-400">
          Your recent reading activity. Login to sync across devices.
        </p>
      </header>

      {loading ? (
        <div className="card text-sm text-ink-400">Loading history…</div>
      ) : error ? (
        <div className="card text-sm text-sakura-300">
          {error} — <Link href="/login" className="text-sakura-400 underline">Login</Link>
        </div>
      ) : entries.length === 0 ? (
        <div className="card text-sm text-ink-400">
          No history yet. Start reading something from the{" "}
          <Link href="/" className="text-sakura-400 underline">home page</Link>.
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((e) => {
            const meta = KIND_LABELS[e.content_type] || { label: e.content_type, color: "bg-ink-700" };
            return (
              <Link
                key={e.id}
                href={buildHref(e)}
                className="card card-hover flex items-center justify-between gap-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase text-white ${meta.color}`}>
                      {meta.label}
                    </span>
                    <span className="text-[10px] text-ink-400 sm:text-xs">{e.source}</span>
                  </div>
                  <h3 className="mt-1 truncate text-sm font-semibold sm:text-base">
                    {e.content_id} <span className="text-ink-500">›</span> {e.chapter_id}
                  </h3>
                  <p className="text-[10px] text-ink-500 sm:text-xs">
                    Read {new Date(e.read_at).toLocaleString()}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-sakura-400">Resume →</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
