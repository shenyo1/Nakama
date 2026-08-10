"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ANIME_SOURCES, COMIC_SOURCES, NOVEL_SOURCES, PUBLIC_API_BASE } from "../lib/api";
import {
  IconDeviceTv,
  IconBooks,
  IconBook,
  IconSearch,
  IconWorld,
  IconBolt,
  IconBookmark,
  IconSettings,
} from "@tabler/icons-react";


interface UserInfo {
  id?: number;
  username?: string;
  email?: string;
  plan?: string;
}

interface QuotaInfo {
  plan: string;
  remaining: number;
  limit: number;
  used: number;
}

export default function HomePage() {
  const [mounted, setMounted] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [history, setHistory] = useState<
    { kind: string; source: string; title: string; slug: string; read_at: string }[]
  >([]);

  useEffect(() => {
    setMounted(true);
    const token = localStorage.getItem("nakama_token");
    const raw = localStorage.getItem("nakama_user");
    if (token) {
      setAuthed(true);
      if (raw) setUser(JSON.parse(raw));

      const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      };

      fetch(`${PUBLIC_API_BASE}/auth/quota`, { headers })
        .then((r) => r.json())
        .then((d) => {
          if (d.ok && d.data) setQuota(d.data);
        })
        .catch(() => {});

      fetch(`${PUBLIC_API_BASE}/history?limit=5`, { headers })
        .then((r) => r.json())
        .then((d) => {
          if (d.ok && d.data && Array.isArray(d.data)) setHistory(d.data);
        })
        .catch(() => {});
    }
  }, []);

  const totalSources = ANIME_SOURCES.length + COMIC_SOURCES.length + NOVEL_SOURCES.length;

  if (!mounted) {
    return (
      <div className="space-y-8 sm:space-y-12">
        <div className="space-y-4 pt-4">
          <div className="h-4 w-48 rounded bg-ink-800 animate-pulse" />
          <div className="h-12 w-3xl max-w-3xl rounded bg-ink-800 animate-pulse" />
          <div className="h-4 w-2xl max-w-2xl rounded bg-ink-800 animate-pulse" />
        </div>
      </div>
    );
  }

  // ── Logged-in: personal home ──────────────────────────────────────
  if (authed) {
    return (
      <div className="space-y-6 sm:space-y-8 animate-fade-in">
        {/* Welcome header */}
        <section className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sakura-400">
            Welcome back
          </p>
          <h1 className="font-display text-2xl font-bold sm:text-3xl">
            Hi, <span className="text-sakura-400">{user?.username || "user"}</span> 👋
          </h1>
          <p className="text-sm text-ink-400">
            {totalSources} sources available · {quota?.plan || "free"} plan
          </p>
        </section>

        {/* Quick actions */}
        <section className="grid gap-2 sm:gap-4 grid-cols-2 sm:grid-cols-4">
          <QuickLink href="/anime" label="Browse Anime" sub={`${ANIME_SOURCES.length} sources`} Icon={IconDeviceTv} />
          <QuickLink href="/comic" label="Browse Comics" sub={`${COMIC_SOURCES.length} sources`} Icon={IconBooks} />
          <QuickLink href="/novel" label="Browse Novels" sub={`${NOVEL_SOURCES.length} sources`} Icon={IconBook} />
          <QuickLink href="/search" label="Cross-Search" sub="All sources" Icon={IconSearch} />
        </section>

        {/* Quota + Analytics */}
        <section className="grid gap-2 sm:gap-4 md:grid-cols-2">
          <div className="card">
            <h3 className="mb-3 font-semibold text-sm">Usage Quota</h3>
            {quota ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-ink-400">Plan</span>
                  <span className="font-mono text-sakura-400">{quota.plan}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-ink-400">Remaining</span>
                  <span className="font-mono tabular-nums text-ink-50">{quota.remaining}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-ink-400">Used</span>
                  <span className="font-mono tabular-nums text-ink-300">
                    {quota.used} / {quota.limit}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-sakura-500 to-neon-500 transition-all"
                    style={{
                      width: `${quota.limit > 0 ? Math.min(100, (quota.used / quota.limit) * 100) : 0}%`,
                    }}
                    role="progressbar"
                    aria-valuenow={quota.used}
                    aria-valuemax={quota.limit}
                  />
                </div>
              </div>
            ) : (
              <p className="text-sm text-ink-400">Loading quota…</p>
            )}
            <Link href="/dashboard" className="mt-3 block text-xs text-sakura-400 hover:underline">
              View full dashboard →
            </Link>
            <Link href="/change-password" className="mt-1 block text-xs text-ink-500 hover:text-sakura-400">
              Change password →
            </Link>
          </div>

          <div className="card">
            <h3 className="mb-3 font-semibold text-sm">Recent Reading</h3>
            {history.length > 0 ? (
              <ul className="space-y-2">
                {history.map((h, i) => (
                  <li key={i} className="text-sm">
                    <Link
                      href={`/${h.kind}/${h.source}/detail/${h.slug}`}
                      className="text-ink-200 hover:text-sakura-400 hover:underline"
                    >
                      {h.title}
                    </Link>
                    <p className="text-xs text-ink-500">
                      {h.kind} · {h.source} · {new Date(h.read_at).toLocaleDateString()}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-400">
                No reading history yet.{" "}
                <Link href="/anime" className="text-sakura-400 hover:underline">
                  Start browsing →
                </Link>
              </p>
            )}
            <Link href="/history" className="mt-3 block text-xs text-sakura-400 hover:underline">
              View all history →
            </Link>
          </div>
        </section>
      </div>
    );
  }

  // ── Logged-out: marketing landing ─────────────────────────────────
  return (
    <div className="space-y-8 sm:space-y-12 animate-fade-in">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl">
        {/* Animated background glow */}
        <div className="absolute inset-0 bg-hero-gradient opacity-60" />
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-sakura-500/20 blur-3xl animate-pulse" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-neon-500/20 blur-3xl animate-pulse" style={{ animationDelay: "1s" }} />

        <div className="relative space-y-5 p-6 sm:p-10 lg:p-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-sakura-400/30 bg-sakura-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sakura-300">
            <span className="h-1.5 w-1.5 rounded-full bg-sakura-400 animate-pulse" />
            {totalSources} sources · 1 API
          </div>

          <h1 className="max-w-3xl font-display text-3xl font-bold leading-tight sm:text-4xl sm:text-5xl lg:text-6xl">
            Your universe for{" "}
            <span className="bg-gradient-to-r from-sakura-400 via-sakura-300 to-neon-400 bg-clip-text text-transparent">
              anime, manga & novels
            </span>
          </h1>

          <p className="max-w-2xl text-sm text-ink-300 leading-relaxed sm:text-base lg:text-lg">
            Nakama aggregates {totalSources} public sources into one beautiful interface.
            Watch anime, read manga, devour novels. All in one place, powered by a blazing-fast REST API.
          </p>

          <div className="flex flex-wrap gap-2 sm:gap-3">
            <Link href="/anime" className="btn-primary group">
              <IconDeviceTv size={18} stroke={1.5} /> Browse Anime
              <span className="ml-1 transition-transform group-hover:translate-x-0.5">→</span>
            </Link>
            <Link href="/comic" className="btn-primary group">
              <IconBooks size={18} stroke={1.5} /> Read Manga
              <span className="ml-1 transition-transform group-hover:translate-x-0.5">→</span>
            </Link>
            <Link href="/novel" className="btn-ghost group">
              <IconBook size={18} stroke={1.5} /> Novels
            </Link>
            <Link href="/register" className="btn-ghost">
              Create Account
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid gap-2 sm:gap-4 grid-cols-2 sm:grid-cols-4">
        <StatCard label="Total sources" value={totalSources} Icon={IconWorld} />
        <StatCard label="Anime" value={ANIME_SOURCES.length} Icon={IconDeviceTv} />
        <StatCard label="Manga & Comics" value={COMIC_SOURCES.length} Icon={IconBooks} />
        <StatCard label="Novels" value={NOVEL_SOURCES.length} Icon={IconBook} />
      </section>

      {/* Feature highlights */}
      <section className="grid gap-3 sm:gap-6 md:grid-cols-3 md:grid-rows-2">
        <FeatureCard
          title="Unified Search"
          description={`Search across all ${totalSources} sources simultaneously. Results are automatically deduplicated and ranked by coverage. No more switching between sites.`}
          href="/search"
          featured
          className="md:col-span-2 md:row-span-2"
          Icon={IconSearch}
        />
        <FeatureCard
          title="Live Updates"
          description="WebSocket streams keep you informed of new chapters and source health in real-time."
          href="/status"
          Icon={IconBolt}
        />
        <FeatureCard
          title="Reading History"
          description="Sync bookmarks and track progress across all your devices."
          href="/register"
          Icon={IconBookmark}
        />
        <FeatureCard
          title="Developer API"
          description="Full REST API with OpenAPI docs, TypeScript SDK, and MCP tools for AI agents."
          href="https://api.mynakama.web.id/docs"
          external
          className="md:col-span-2"
          Icon={IconSettings}
        />
      </section>

      {/* Source showcase */}
      <section className="space-y-3">
        <h2 className="font-display text-lg font-bold sm:text-xl">All Sources</h2>
        <div className="flex flex-wrap gap-1.5 sm:gap-2">
          {[...ANIME_SOURCES.map(s => ({ name: s, kind: "anime" })),
            ...COMIC_SOURCES.map(s => ({ name: s, kind: "comic" })),
            ...NOVEL_SOURCES.map(s => ({ name: s, kind: "novel" })),
          ].map((src) => (
            <Link
              key={`${src.kind}-${src.name}`}
              href={`/${src.kind}?source=${src.name}`}
              className={`badge transition hover:scale-105 hover:border-sakura-400/60 ${
                src.kind === "anime" ? "hover:bg-sakura-500/20" :
                src.kind === "comic" ? "hover:bg-neon-500/20" :
                "hover:bg-purple-500/20"
              }`}
            >
              {src.name}
            </Link>
          ))}
        </div>
      </section>

      {/* Footer links */}
      <section className="border-t border-ink-800 pt-4 text-sm text-ink-400 space-y-1 sm:pt-6">
        <p className="flex flex-wrap gap-x-4 gap-y-1">
          <a
            href="https://github.com/shenyo1/Nakama"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          <a
            href="https://api.mynakama.web.id/docs"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            API Docs
          </a>
          <a
            href="https://api.mynakama.web.id/sources/health"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            Health Status
          </a>
        </p>
      </section>
    </div>
  );
}

function StatCard({ label, value, Icon }: { label: string; value: string | number; Icon: any }) {
  return (
    <div className="card card-hover group">
      <div className="flex items-center justify-between">
        <p className="text-xs text-ink-400">{label}</p>
        <span className="opacity-50 transition group-hover:opacity-100 group-hover:scale-110"><Icon size={20} stroke={1.5} /></span>
      </div>
      <p className="mt-1 text-2xl font-bold text-ink-50 tabular-nums sm:text-3xl">{value}</p>
    </div>
  );
}

function QuickLink({ href, label, sub, Icon }: { href: string; label: string; sub: string; Icon: any }) {
  return (
    <Link href={href} className="card card-hover text-center group">
      <div className="mb-1 flex justify-center"><Icon size={28} stroke={1.5} className="text-sakura-300 transition group-hover:scale-110" /></div>
      <p className="font-semibold text-sm sm:text-base">{label}</p>
      <p className="mt-1 text-xs text-ink-400">{sub}</p>
    </Link>
  );
}

function FeatureCard({
  title,
  description,
  href,
  featured,
  className = "",
  Icon,
  external,
}: {
  title: string;
  description: string;
  href?: string;
  featured?: boolean;
  className?: string;
  Icon?: any;
  external?: boolean;
}) {
  const inner = (
    <div
      className={`card card-hover h-full ${featured ? "md:p-8" : ""} ${className}`}
    >
      {Icon && (
        <div className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-sakura-500/20 to-neon-500/20 ${featured ? "sm:h-12 sm:w-12" : ""}`}>
          <Icon size={featured ? 24 : 20} stroke={1.5} className="text-sakura-300" />
        </div>
      )}
      <h3 className={`font-semibold mb-2 ${featured ? "text-lg sm:text-xl" : "text-sm sm:text-base"}`}>
        {title}
      </h3>
      <p
        className={`text-ink-400 leading-relaxed ${featured ? "text-sm sm:text-base max-w-[55ch]" : "text-sm"}`}
      >
        {description}
      </p>
      {href && (
        <span className={`mt-3 inline-block text-xs text-sakura-400 ${featured ? "sm:text-sm" : ""}`}>
          Learn more →
        </span>
      )}
    </div>
  );
  if (href) {
    if (external) {
      return (
        <a href={href} target="_blank" rel="noreferrer" className={`block h-full ${className}`}>
          {inner}
        </a>
      );
    }
    return (
      <Link href={href} className={`block h-full ${className}`}>
        {inner}
      </Link>
    );
  }
  return <div className={className}>{inner}</div>;
}
