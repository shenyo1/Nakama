"use client";

import { useEffect, useState } from "react";

interface Review {
  id: number;
  user_id: number;
  username: string;
  source: string;
  slug: string;
  kind: string;
  rating: number;
  body: string;
  created_at: string;
}

interface ReviewAggregate {
  count: number;
  avg_rating: number;
  distribution: Record<number, number>;
}

interface ReviewListProps {
  source: string;
  slug: string;
  kind?: "anime" | "comic" | "novel";
}

export function ReviewList({ source, slug, kind }: ReviewListProps) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [stats, setStats] = useState<ReviewAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  async function loadReviews() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (kind) params.set("kind", kind);

      const [revRes, statsRes] = await Promise.all([
        fetch(`${apiBase}/reviews/${encodeURIComponent(source)}/${encodeURIComponent(slug)}?${params}`),
        fetch(`${apiBase}/reviews/${encodeURIComponent(source)}/${encodeURIComponent(slug)}/stats?${params}`),
      ]);

      if (revRes.ok) {
        const data = await revRes.json();
        setReviews(Array.isArray(data) ? data : []);
      }
      if (statsRes.ok) {
        const s = await statsRes.json();
        setStats(s);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReviews();
  }, [source, slug, kind]);

  if (loading) {
    return (
      <div className="card space-y-3 animate-pulse">
        <div className="h-4 w-24 bg-ink-800 rounded" />
        <div className="h-3 w-full bg-ink-800 rounded" />
        <div className="h-3 w-3/4 bg-ink-800 rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      {stats && (
        <div className="card flex flex-wrap items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-1.5">
            <span className="text-amber-400 text-lg">★</span>
            <span className="text-lg font-bold tabular-nums">{stats.avg_rating}</span>
            <span className="text-xs text-ink-400">({stats.count} reviews)</span>
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {[5, 4, 3, 2, 1].map((r) => (
              <span
                key={r}
                className="inline-flex items-center gap-1 rounded-full bg-ink-800 px-2 py-0.5 text-xs"
              >
                <span className="text-amber-400">★</span>
                <span className="tabular-nums">{stats.distribution[r] || 0}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Reviews */}
      {error && <p className="text-xs text-rose-400">{error}</p>}

      {reviews.length === 0 && !error ? (
        <p className="text-sm text-ink-400">No reviews yet. Be the first!</p>
      ) : (
        <div className="space-y-3">
          {reviews.map((r) => (
            <div key={r.id} className="card">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{r.username || `User #${r.user_id}`}</span>
                  <span className="text-amber-400 text-xs">
                    {"★".repeat(r.rating)}{"☆".repeat(5 - r.rating)}
                  </span>
                </div>
                <time className="text-xs text-ink-500" dateTime={r.created_at}>
                  {new Date(r.created_at).toLocaleDateString()}
                </time>
              </div>
              <p className="text-sm text-ink-200 leading-relaxed whitespace-pre-wrap">{r.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
