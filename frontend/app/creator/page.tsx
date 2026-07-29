"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PUBLIC_API_BASE } from "@/lib/api";

interface CreatorItem {
  id: number;
  display_name: string;
  avatar_url: string | null;
  bio: string | null;
  follower_count: number;
  series_count: number;
  verified: boolean;
}

export default function CreatorBrowsePage() {
  const [creators, setCreators] = useState<CreatorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${PUBLIC_API_BASE}/creator/browse?limit=50`);
        if (!res.ok) throw new Error(`${res.status}`);
        const data = await res.json();
        setCreators(data);
      } catch (e: any) {
        setError(e.message || String(e));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 rounded bg-ink-800" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded bg-ink-800/50" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold sm:text-3xl">Creators</h1>
        <p className="text-sm text-ink-400">
          Discover independent creators publishing stories, comics, and art on Nakama.
        </p>
      </header>

      {error && (
        <div className="card text-sm text-sakura-200">{error}</div>
      )}

      {creators.length === 0 ? (
        <p className="text-sm text-ink-400">No creators yet. Be the first!</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {creators.map((c) => (
            <Link
              key={c.id}
              href={`/creator/${c.id}`}
              className="card flex items-start gap-4 hover:border-sakura-500/30 transition-colors"
            >
              <div className="h-14 w-14 rounded-full bg-ink-700 flex items-center justify-center text-xl text-ink-400 shrink-0">
                {c.avatar_url ? (
                  <img src={c.avatar_url} alt="" className="h-full w-full rounded-full object-cover" />
                ) : (
                  c.display_name[0]?.toUpperCase() || "?"
                )}
              </div>
              <div className="min-w-0">
                <h2 className="font-semibold flex items-center gap-1">
                  {c.display_name}
                  {c.verified && (
                    <span className="text-xs text-sakura-400" title="Verified">✓</span>
                  )}
                </h2>
                {c.bio && (
                  <p className="mt-0.5 text-xs text-ink-400 line-clamp-2">{c.bio}</p>
                )}
                <p className="mt-1 text-xs text-ink-500">
                  {c.series_count} series · {c.follower_count} followers
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
