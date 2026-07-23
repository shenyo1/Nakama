"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ANIME_SOURCES, COMIC_SOURCES, NOVEL_SOURCES, PUBLIC_API_BASE } from "../lib/api";

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

      // Fetch quota + recent history in parallel
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

  // Don't flash wrong content during hydration
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
      <div className="space-y-6 sm:space-y-8">
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
          <QuickLink href="/anime" label="Browse Anime" sub={`${ANIME_SOURCES.length} sources`} />
          <QuickLink href="/comic" label="Browse Comics" sub={`${COMIC_SOURCES.length} sources`} />
          <QuickLink href="/novel" label="Browse Novels" sub={`${NOVEL_SOURCES.length} sources`} />
          <QuickLink href="/search" label="Cross-Search" sub="All sources" />
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
                {/* Progress bar */}
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-ink-800">
                  <div
                    className="h-full rounded-full bg-sakura-500 transition-all"
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
    <div className="space-y-8 sm:space-y-12">
      {/* Hero */}
      <section className="space-y-4 pt-4 sm:space-y-5">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sakura-400">
          Multi-source aggregation API
        </p>
        <h1 className="max-w-3xl font-display text-3xl font-bold leading-tight sm:text-4xl sm:text-5xl">
          Browse anime, comics and novels from{" "}
          <span className="text-sakura-400">{totalSources} sources</span>{" "}
          through one REST API.
        </h1>
        <p className="max-w-2xl text-sm text-ink-300 leading-relaxed sm:text-base">
          Nakama aggregates {totalSources} public sources ({ANIME_SOURCES.length} anime,
          {" "}{COMIC_SOURCES.length} comic, {NOVEL_SOURCES.length} novel) behind
          a consistent JSON interface. Multi-source search with automatic
          deduplication, offline fixtures, WebSocket live updates, auto-repair
          circuit breakers, and a generated TypeScript SDK.
        </p>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <Link href="/anime" className="btn-primary">
            Browse Anime
          </Link>
          <Link href="/comic" className="btn-primary">
            Browse Comics
          </Link>
          <Link href="/register" className="btn-ghost">
            Create Account
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="grid gap-2 sm:gap-4 grid-cols-2 sm:grid-cols-4">
        <StatCard label="Total sources" value={totalSources} />
        <StatCard label="Anime sources" value={ANIME_SOURCES.length} />
        <StatCard label="Comic sources" value={COMIC_SOURCES.length} />
        <StatCard label="Novel sources" value={NOVEL_SOURCES.length} />
      </section>

      {/* Feature highlights */}
      <section className="grid gap-3 sm:gap-6 md:grid-cols-2">
        <FeatureCard
          title="Multi-source search"
          description={`Search across all ${COMIC_SOURCES.length} comic, ${ANIME_SOURCES.length} anime, or ${NOVEL_SOURCES.length} novel sources at once. Results are deduplicated and ranked by coverage.`}
          href="/search"
        />
        <FeatureCard
          title="Auto-repair and resilience"
          description="Circuit breakers, domain rotation, proxy pools, DNS watchdog, and auto-restart keep sources healthy 24/7."
          href="/status"
        />
        <FeatureCard
          title="Personal reading history"
          description="Create an account to sync bookmarks, track reading progress, and personalize your experience across devices."
          href="/register"
        />
        <FeatureCard
          title="TypeScript SDK"
          description="Generated from OpenAPI schema. 58 endpoints, 22 schemas. Drop it into any frontend project."
        />
      </section>

      {/* Footer links */}
      <section className="border-t border-ink-800 pt-4 text-sm text-ink-400 space-y-1 sm:pt-6">
        <p>
          <a
            href="https://github.com/shenyo1/Nakama"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
          {" · "}
          <a
            href="https://mynakama.web.id/docs"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            API Docs
          </a>
          {" · "}
          <a
            href="https://mynakama.web.id/sources/health"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            Health JSON
          </a>
        </p>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-ink-50 tabular-nums sm:text-3xl">{value}</p>
    </div>
  );
}

function QuickLink({ href, label, sub }: { href: string; label: string; sub: string }) {
  return (
    <Link href={href} className="card card-hover text-center">
      <p className="font-semibold text-sm sm:text-base">{label}</p>
      <p className="mt-1 text-xs text-ink-400">{sub}</p>
    </Link>
  );
}

function FeatureCard({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href?: string;
}) {
  const inner = (
    <div className="card card-hover h-full">
      <h3 className="font-semibold mb-2 text-sm sm:text-base">{title}</h3>
      <p className="text-sm text-ink-400 leading-relaxed">{description}</p>
    </div>
  );
  if (href) {
    return (
      <Link href={href} className="block h-full">
        {inner}
      </Link>
    );
  }
  return inner;
}
