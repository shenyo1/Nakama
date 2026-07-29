"use client";

import { useEffect, useState } from "react";

interface StreakData {
  current_streak: number;
  longest_streak: number;
  total_read: number;
  today_read: number;
  goal: number;
  goal_met: boolean;
  last_read_date: string | null;
  badges: string[];
}

const ALL_BADGES: Record<string, { emoji: string; label: string; description: string }> = {
  first_read: { emoji: "📖", label: "First Read", description: "Read your first chapter" },
  streak_3: { emoji: "🔥", label: "3-Day Streak", description: "Read 3 days in a row" },
  streak_7: { emoji: "💪", label: "Weekly Warrior", description: "Read 7 days in a row" },
  streak_30: { emoji: "👑", label: "Monthly Master", description: "Read 30 days in a row" },
  read_10: { emoji: "📚", label: "Bookworm", description: "Read 10 chapters" },
  read_50: { emoji: "📚📚", label: "Bibliophile", description: "Read 50 chapters" },
  read_100: { emoji: "🏆", label: "Century Club", description: "Read 100 chapters" },
  genre_explorer: { emoji: "🧭", label: "Explorer", description: "Read from 5 different genres" },
  night_owl: { emoji: "🦉", label: "Night Owl", description: "Read after midnight" },
  speed_demon: { emoji: "⚡", label: "Speed Demon", description: "Read 10 chapters in one day" },
};

export default function ReadingGoals() {
  const [streak, setStreak] = useState<StreakData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("nakama_token");
    if (!token) {
      setLoading(false);
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_BASE || "https://mynakama.web.id"}/user/streak`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok && d.data) setStreak(d.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="card animate-pulse space-y-3">
        <div className="h-4 w-24 rounded bg-ink-800" />
        <div className="h-8 w-32 rounded bg-ink-800" />
      </div>
    );
  }

  if (!streak) return null;

  const progress = streak.goal > 0 ? Math.min(100, (streak.today_read / streak.goal) * 100) : 0;

  return (
    <div className="card space-y-4">
      {/* Streak header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">📊 Reading Goals</h3>
        <span className="text-[10px] text-ink-500">Daily goal: {streak.goal} chapters</span>
      </div>

      {/* Streak counter */}
      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold tabular-nums text-sakura-400">
            {streak.current_streak}
          </div>
          <div className="text-[10px] text-ink-400">day streak</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold tabular-nums text-amber-400">
            {streak.longest_streak}
          </div>
          <div className="text-[10px] text-ink-400">best streak</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold tabular-nums text-emerald-400">
            {streak.total_read}
          </div>
          <div className="text-[10px] text-ink-400">total read</div>
        </div>
      </div>

      {/* Today's progress */}
      <div>
        <div className="mb-1 flex justify-between text-xs">
          <span className="text-ink-400">Today</span>
          <span className="tabular-nums text-ink-200">
            {streak.today_read} / {streak.goal}
            {streak.goal_met && " ✅"}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-ink-800">
          <div
            className={`h-full rounded-full transition-all ${
              streak.goal_met ? "bg-emerald-500" : "bg-sakura-500"
            }`}
            style={{ width: `${progress}%` }}
            role="progressbar"
            aria-valuenow={streak.today_read}
            aria-valuemax={streak.goal}
          />
        </div>
      </div>

      {/* Badges */}
      {streak.badges.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-medium text-ink-400">🏅 Badges</h4>
          <div className="flex flex-wrap gap-2">
            {streak.badges.map((badge) => {
              const info = ALL_BADGES[badge];
              if (!info) return null;
              return (
                <div
                  key={badge}
                  className="group relative flex items-center gap-1.5 rounded-full bg-ink-800 px-2.5 py-1 text-xs"
                  title={info.description}
                >
                  <span>{info.emoji}</span>
                  <span className="text-ink-300">{info.label}</span>
                  {/* Tooltip */}
                  <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-ink-950 px-2 py-1 text-[10px] text-ink-200 opacity-0 transition-opacity group-hover:opacity-100">
                    {info.description}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* All badges (locked) */}
      <div>
        <h4 className="mb-2 text-xs font-medium text-ink-400">🔒 Locked</h4>
        <div className="flex flex-wrap gap-2">
          {Object.entries(ALL_BADGES)
            .filter(([key]) => !streak.badges.includes(key))
            .slice(0, 6)
            .map(([key, info]) => (
              <div
                key={key}
                className="flex items-center gap-1.5 rounded-full bg-ink-900/50 px-2.5 py-1 text-xs opacity-50"
              >
                <span>{info.emoji}</span>
                <span className="text-ink-500">{info.label}</span>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
