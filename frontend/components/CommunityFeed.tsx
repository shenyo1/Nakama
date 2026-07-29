"use client";

import { useEffect, useState } from "react";

interface FeedItem {
  type: "review" | "comment" | "list";
  user_id: number;
  username: string;
  data: Record<string, unknown>;
  created_at: string;
}

export function CommunityFeed() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<string>("");

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  async function loadFeed() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "30" });
      if (kind) params.set("kind", kind);
      const res = await fetch(`${apiBase}/community/feed?${params}`);
      if (res.ok) {
        const data = await res.json();
        setItems(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadFeed();
  }, [kind]);

  const kindOptions = ["", "anime", "comic", "novel"];

  function feedIcon(type: string): string {
    switch (type) {
      case "review":
        return "★";
      case "comment":
        return "💬";
      case "list":
        return "📋";
      default:
        return "•";
    }
  }

  function feedColor(type: string): string {
    switch (type) {
      case "review":
        return "text-amber-400";
      case "comment":
        return "text-sky-400";
      case "list":
        return "text-emerald-400";
      default:
        return "text-ink-400";
    }
  }

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-ink-400">Filter:</span>
        {kindOptions.map((k) => (
          <button
            key={k}
            onClick={() => setKind(k)}
            className={`rounded-full px-3 py-1 text-xs transition-colors ${
              kind === k
                ? "bg-sakura-600 text-white"
                : "bg-ink-800 text-ink-300 hover:bg-ink-700"
            }`}
          >
            {k || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card">
              <div className="h-3 w-1/4 bg-ink-800 rounded mb-2" />
              <div className="h-3 w-3/4 bg-ink-800 rounded" />
            </div>
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-rose-400">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-ink-400">No community activity yet.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item, i) => (
            <div key={`${item.type}-${i}`} className="card flex gap-3">
              <span className={`text-lg shrink-0 ${feedColor(item.type)}`}>
                {feedIcon(item.type)}
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium">{item.username || `User #${item.user_id}`}</span>
                  <span className={`text-[10px] uppercase ${feedColor(item.type)}`}>
                    {item.type}
                  </span>
                  <time className="text-[10px] text-ink-500" dateTime={item.created_at}>
                    {new Date(item.created_at).toLocaleString()}
                  </time>
                </div>
                {item.type === "review" && (
                  <p className="text-sm text-ink-200">
                    Rated {String(item.data.kind)}/{String(item.data.source)}/{String(item.data.slug)}{" "}
                    <span className="text-amber-400">{"★".repeat(Number(item.data.rating) || 0)}</span>
                    {" "}
                    <span className="text-ink-400 text-xs">{String(item.data.body || "").slice(0, 150)}</span>
                  </p>
                )}
                {item.type === "comment" && (
                  <p className="text-sm text-ink-200">
                    Commented on {String(item.data.kind)}/{String(item.data.source)}/{String(item.data.slug)}{" "}
                    <span className="text-ink-400 text-xs">{String(item.data.body || "").slice(0, 150)}</span>
                  </p>
                )}
                {item.type === "list" && (
                  <p className="text-sm text-ink-200">
                    Created reading list{" "}
                    <span className="text-emerald-300 font-medium">{String(item.data.name)}</span>
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
