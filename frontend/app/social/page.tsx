"use client";

import { useCallback, useEffect, useState } from "react";
import {
  fetchActivity,
  fetchClubs,
  fetchLeaderboard,
  type ActivityRow,
  type ClubRow,
  type LeaderboardRow,
} from "@/lib/api";
import { PUBLIC_API_BASE } from "@/lib/api";

type Tab = "leaderboard" | "activity" | "clubs";

const MEDALS = ["🥇", "🥈", "🥉"];

const ACTION_LABEL: Record<string, string> = {
  read: "membaca",
  rate: "menilai",
  comment: "mengomentari",
  list: "membuat list",
  follow: "mengikuti",
  bookmark: "menandai",
  create_club: "membuat klub",
  join_club: "bergabung klub",
};

function timeAgo(iso?: string | null): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  const s = Math.floor((Date.now() - t) / 1000);
  if (s < 60) return "baru saja";
  if (s < 3600) return `${Math.floor(s / 60)}m lalu`;
  if (s < 86400) return `${Math.floor(s / 3600)}j lalu`;
  return `${Math.floor(s / 86400)}h lalu`;
}

export default function SocialPage() {
  const [tab, setTab] = useState<Tab>("leaderboard");
  const [lb, setLb] = useState<LeaderboardRow[]>([]);
  const [feed, setFeed] = useState<ActivityRow[]>([]);
  const [clubs, setClubs] = useState<ClubRow[]>([]);
  const [loading, setLoading] = useState(true);
  // club creation
  const [showNewClub, setShowNewClub] = useState(false);
  const [clubName, setClubName] = useState("");
  const [clubDesc, setClubDesc] = useState("");
  const [userToken, setUserToken] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    try {
      const t = localStorage.getItem("nakama_token");
      setUserToken(t);
    } catch {}
  }, []);

  const loadTab = useCallback(async (t: Tab) => {
    setLoading(true);
    try {
      if (t === "leaderboard") setLb(await fetchLeaderboard(20));
      else if (t === "activity") setFeed(await fetchActivity());
      else setClubs(await fetchClubs());
    } catch {
      setLb([]); setFeed([]); setClubs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTab(tab);
  }, [tab, loadTab]);

  async function handleCreateClub(e: React.FormEvent) {
    e.preventDefault();
    if (!userToken || !clubName.trim()) return;
    setNotice(null);
    const res = await fetch(`${PUBLIC_API_BASE}/social/clubs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${userToken}` },
      body: JSON.stringify({ name: clubName.trim(), description: clubDesc.trim() || null }),
    });
    if (res.ok) {
      setClubName(""); setClubDesc(""); setShowNewClub(false);
      setNotice("Klub berhasil dibuat! 🎉");
      loadTab("clubs");
    } else {
      const body = await res.json().catch(() => ({}));
      setNotice(body?.detail ?? "Gagal membuat klub (perlu login).");
    }
  }

  async function handleJoin(id: number) {
    if (!userToken) { setNotice("Login dulu untuk bergabung klub."); return; }
    setNotice(null);
    const res = await fetch(`${PUBLIC_API_BASE}/social/clubs/${id}/join`, {
      method: "POST", headers: { Authorization: `Bearer ${userToken}` },
    });
    setNotice(res.ok ? "Berhasil bergabung! 🎉" : (await res.json().catch(() => ({ detail: "Gagal." })))?.detail ?? "Gagal.");
    loadTab("clubs");
  }

  const tabBtn = (id: Tab, label: string) => (
    <button
      onClick={() => setTab(id)}
      className={`rounded-md px-3 py-1.5 text-sm ${tab === id ? "bg-sakura-500/15 text-sakura-300" : "text-ink-300 hover:bg-ink-800"}`}
    >
      {label}
    </button>
  );

  return (
    <div className="container-page py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">👑 Social Hub</h1>
          <p className="text-sm text-ink-400">Leaderboard, aktivitas pembaca, dan klub.</p>
        </div>
        <div className="flex gap-1">
          {tabBtn("leaderboard", "🏆 Leaderboard")}
          {tabBtn("activity", "📢 Aktivitas")}
          {tabBtn("clubs", "🤝 Klub")}
        </div>
      </div>

      {notice && (
        <div className="mb-4 rounded-lg border border-sakura-500/30 bg-sakura-500/10 px-3 py-2 text-sm">
          {notice}
        </div>
      )}

      {loading && <p className="py-10 text-center text-ink-400">Memuat…</p>}

      {/* ── Leaderboard ─────────────────────────── */}
      {!loading && tab === "leaderboard" && (
        <div className="space-y-2">
          {lb.length === 0 && <p className="py-8 text-center text-ink-500">Belum ada pembaca minggu ini.</p>}
          {lb.map((r) => (
            <div key={r.user_id} className={`flex items-center justify-between rounded-xl border px-4 py-3 ${r.rank <= 3 ? "border-sakura-500/40 bg-ink-900/60" : "border-ink-800 bg-ink-900/30"}`}>
              <div className="flex items-center gap-3">
                <span className="w-8 text-center text-xl">{MEDALS[r.rank - 1] ?? r.rank}</span>
                <div>
                  <p className="font-medium">{r.username}</p>
                  <p className="text-xs text-ink-400">
                    Lv.{r.level} · 🔥 {r.reading_streak} streak
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-bold tabular-nums text-sakura-300">{r.xp} XP</p>
                <p className="text-xs text-ink-500">{r.chapters_week} chapter · 7 hari</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Activity ───────────────────────────── */}
      {!loading && tab === "activity" && (
        <div className="space-y-2">
          {feed.length === 0 && <p className="py-8 text-center text-ink-500">Belum ada aktivitas.</p>}
          {feed.map((a) => (
            <div key={a.id} className="flex items-center gap-3 rounded-xl border border-ink-800 bg-ink-900/30 px-4 py-3">
              <span className="text-lg">📖</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">
                  <span className="font-medium text-sakura-300">{a.username}</span>{" "}
                  {ACTION_LABEL[a.action] ?? a.action}{" "}
                  {a.title && <span className="text-ink-200">&ldquo;{a.title}&rdquo;</span>}
                </p>
                <p className="text-xs text-ink-500">{timeAgo(a.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Clubs ──────────────────────────────── */}
      {!loading && tab === "clubs" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setShowNewClub((v) => !v)}
              className="btn text-sm"
            >
              {showNewClub ? "✕ Tutup" : "+ Buat Klub"}
            </button>
          </div>

          {showNewClub && (
            <form onSubmit={handleCreateClub} className="space-y-3 rounded-xl border border-ink-800 bg-ink-900/40 p-4">
              <input
                value={clubName}
                onChange={(e) => setClubName(e.target.value)}
                placeholder="Nama klub (mis. One Piece Fans)"
                className="w-full rounded-md border border-ink-700 bg-ink-950 px-3 py-2 text-sm focus:border-sakura-400 focus:outline-none"
                required
              />
              <textarea
                value={clubDesc}
                onChange={(e) => setClubDesc(e.target.value)}
                placeholder="Deskripsi (opsional)"
                rows={2}
                className="w-full rounded-md border border-ink-700 bg-ink-950 px-3 py-2 text-sm focus:border-sakura-400 focus:outline-none"
              />
              <button type="submit" className="btn text-sm" disabled={!userToken}>
                {userToken ? "Buat" : "Login untuk membuat"}
              </button>
            </form>
          )}

          {clubs.length === 0 && <p className="py-8 text-center text-ink-500">Belum ada klub.</p>}
          {clubs.map((c) => (
            <div key={c.id} className="flex items-center justify-between rounded-xl border border-ink-800 bg-ink-900/30 px-4 py-3">
              <div className="min-w-0">
                <p className="font-medium">{c.name}</p>
                <p className="truncate text-xs text-ink-400">
                  {c.description || "—"} · {c.member_count} anggota
                </p>
              </div>
              <button
                onClick={() => handleJoin(c.id)}
                className="ml-3 shrink-0 rounded-md border border-sakura-500/40 px-3 py-1 text-xs text-sakura-300 hover:bg-sakura-500/10"
              >
                Gabung
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
