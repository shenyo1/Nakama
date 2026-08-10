"use client";

import { useEffect, useState } from "react";

interface YearStats {
  year: number;
  total_chapters: number;
  total_series: number;
  top_genres: { name: string; count: number }[];
  top_series: { title: string; kind: string; chapters: number; source: string }[];
  most_active_month: string;
  most_active_day: string;
  longest_streak: number;
  total_reading_time_minutes: number;
  favorite_kind: string;
}

export default function YearInManga() {
  const [stats, setStats] = useState<YearStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [year, setYear] = useState(new Date().getFullYear());

  useEffect(() => {
    const token = localStorage.getItem("nakama_token");
    if (!token) {
      setLoading(false);
      return;
    }

    fetch(
      `${process.env.NEXT_PUBLIC_API_BASE || "https://api.mynakama.web.id"}/user/year-stats?year=${year}`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
      .then((r) => r.json())
      .then((d) => {
        if (d.ok && d.data) setStats(d.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [year]);

  if (loading) {
    return (
      <div className="card animate-pulse space-y-4">
        <div className="h-6 w-48 rounded bg-ink-800" />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded bg-ink-800" />
          ))}
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="card text-center text-sm text-ink-400">
        <p className="mb-2 text-2xl">📊</p>
        <p>Start reading to see your Year in Manga!</p>
        <p className="mt-1 text-xs">
          Your reading stats will appear here after you read some chapters.
        </p>
      </div>
    );
  }

  const kindEmoji = stats.favorite_kind === "anime" ? "🎬" : stats.favorite_kind === "comic" ? "📚" : "📖";

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="overflow-hidden rounded-2xl bg-gradient-to-br from-sakura-600 via-purple-700 to-indigo-800 p-6 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] opacity-70">
          Your Year in Manga
        </p>
        <h2 className="mt-2 font-display text-3xl font-bold sm:text-4xl">{stats.year}</h2>
        <p className="mt-3 text-sm opacity-80">
          {stats.total_chapters} chapters across {stats.total_series} series
        </p>
        <div className="mt-4 flex gap-3">
          <div className="rounded-full bg-white/20 px-3 py-1 text-xs backdrop-blur">
            {kindEmoji} {stats.favorite_kind} fan
          </div>
          <div className="rounded-full bg-white/20 px-3 py-1 text-xs backdrop-blur">
            🔥 {stats.longest_streak} day streak
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="card text-center">
          <p className="text-2xl font-bold tabular-nums text-sakura-400">{stats.total_chapters}</p>
          <p className="mt-1 text-xs text-ink-400">Chapters</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold tabular-nums text-amber-400">{stats.total_series}</p>
          <p className="mt-1 text-xs text-ink-400">Series</p>
        </div>
        <div className="card text-center">
          <p className="text-2xl font-bold tabular-nums text-emerald-400">
            {Math.round(stats.total_reading_time_minutes / 60)}h
          </p>
          <p className="mt-1 text-xs text-ink-400">Reading</p>
        </div>
      </div>

      {/* Top genres */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold">🎯 Top Genres</h3>
        <div className="space-y-2">
          {stats.top_genres.slice(0, 5).map((g, i) => (
            <div key={g.name} className="flex items-center gap-2">
              <span className="w-5 text-right text-xs tabular-nums text-ink-400">#{i + 1}</span>
              <div className="flex-1">
                <div className="flex justify-between text-xs">
                  <span className="text-ink-200">{g.name}</span>
                  <span className="tabular-nums text-ink-400">{g.count}</span>
                </div>
                <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-ink-800">
                  <div
                    className="h-full rounded-full bg-sakura-500"
                    style={{
                      width: `${(g.count / stats.top_genres[0].count) * 100}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top series */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold">🏆 Most Read</h3>
        <div className="space-y-2">
          {stats.top_series.slice(0, 5).map((s, i) => (
            <a
              key={s.title}
              href={s.kind === "comic"
                ? `/manga/${s.source}/${s.title.toLowerCase().replace(/\s+/g, "-")}`
                : `/${s.kind}/${s.source}/detail/${s.title.toLowerCase().replace(/\s+/g, "-")}`
              }
              className="flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-ink-800/50"
            >
              <span className="text-lg font-bold tabular-nums text-ink-400">#{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink-100">{s.title}</p>
                <p className="text-xs text-ink-400">
                  {s.chapters} chapters · {s.kind}
                </p>
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* Fun facts */}
      <div className="card">
        <h3 className="mb-3 text-sm font-semibold">💡 Fun Facts</h3>
        <div className="space-y-2 text-xs">
          <p className="flex items-center gap-2">
            <span>📅</span>
            <span className="text-ink-400">
              Most active month: <span className="text-ink-200">{stats.most_active_month}</span>
            </span>
          </p>
          <p className="flex items-center gap-2">
            <span>🌙</span>
            <span className="text-ink-400">
              Favorite day: <span className="text-ink-200">{stats.most_active_day}</span>
            </span>
          </p>
          <p className="flex items-center gap-2">
            <span>🔥</span>
            <span className="text-ink-400">
              Longest streak: <span className="text-ink-200">{stats.longest_streak} days</span>
            </span>
          </p>
          <p className="flex items-center gap-2">
            <span>⏱️</span>
            <span className="text-ink-400">
              Total reading:{" "}
              <span className="text-ink-200">
                {Math.round(stats.total_reading_time_minutes / 60)} hours
              </span>
            </span>
          </p>
        </div>
      </div>

      {/* Share */}
      <div className="text-center">
        <button
          onClick={() => {
            const text = `📊 My ${stats.year} in Manga!\n\n${stats.total_chapters} chapters · ${stats.total_series} series · ${stats.favorite_kind} fan\nTop genre: ${stats.top_genres[0]?.name}\n\n#NakamaWrapped`;
            if (navigator.share) {
              navigator.share({ title: "My Year in Manga", text, url: window.location.href });
            } else {
              window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, "_blank");
            }
          }}
          className="btn-primary text-sm"
        >
          📤 Share Your Stats
        </button>
      </div>
    </div>
  );
}
