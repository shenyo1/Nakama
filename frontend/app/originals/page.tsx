"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "../../lib/api";

interface OriginalSeries {
  id: number;
  title: string;
  slug: string;
  content_type: string;
  synopsis: string | null;
  cover_url: string | null;
  banner_url: string | null;
  author_name: string;
  author_bio: string | null;
  genres: string | null;
  status: string;
  featured: boolean;
  views: number;
  created_at: string;
  updated_at: string;
}

interface PaginatedOriginals {
  items: OriginalSeries[];
  page: number;
  page_size: number;
  total: number;
}

export default function OriginalsPage() {
  const [mounted, setMounted] = useState(false);
  const [series, setSeries] = useState<OriginalSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    fetch(`${PUBLIC_API_BASE}/originals?featured=true&page_size=12`)
      .then((r) => r.json())
      .then((d) => {
        if (d.ok && d.data) {
          const data = d.data as PaginatedOriginals;
          setSeries(data.items || []);
        } else {
          setError("Failed to load originals");
        }
      })
      .catch(() => setError("Failed to load originals"))
      .finally(() => setLoading(false));
  }, []);

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

  return (
    <div className="space-y-8 sm:space-y-12">
      {/* ── Hero ──────────────────────────────────────── */}
      <section className="space-y-4 pt-4 sm:space-y-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sakura-400">
          Nakama Originals
        </p>
        <h1 className="max-w-3xl font-display text-3xl font-bold leading-tight sm:text-4xl sm:text-5xl">
          Discover Original Indonesian{" "}
          <span className="text-sakura-400">Comics &amp; Novels</span>
        </h1>
        <p className="max-w-2xl text-sm text-ink-300 leading-relaxed sm:text-base">
          Exclusive stories from talented Indonesian creators. Read unique comics
          and novels you won&apos;t find anywhere else — directly supporting the
          creators who make them.
        </p>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <a href="#featured" className="btn-primary">
            Browse Featured
          </a>
          <a href="#apply" className="btn-ghost">
            Become a Creator
          </a>
        </div>
      </section>

      {/* ── Featured Grid ────────────────────────────── */}
      <section id="featured" className="space-y-4">
        <h2 className="font-display text-xl font-bold sm:text-2xl">
          Featured Series
        </h2>

        {loading && (
          <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="card space-y-3">
                <div className="aspect-[3/4] rounded-lg bg-ink-800 animate-pulse" />
                <div className="h-4 w-3/4 rounded bg-ink-800 animate-pulse" />
                <div className="h-3 w-1/2 rounded bg-ink-800 animate-pulse" />
              </div>
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="card border-amber-500/30 text-center py-8">
            <p className="text-amber-400">{error}</p>
            <p className="text-sm text-ink-400 mt-1">
              The originals database may be empty. Start by applying as a creator!
            </p>
          </div>
        )}

        {!loading && !error && series.length === 0 && (
          <div className="card border-sakura-400/20 text-center py-12">
            <p className="text-lg text-ink-300 font-semibold">
              No originals yet — be the first!
            </p>
            <p className="text-sm text-ink-400 mt-2">
              Nakama Originals is waiting for its first creators. Apply below to
              publish your work.
            </p>
            <a href="#apply" className="btn-primary mt-4 inline-flex">
              Apply as Creator
            </a>
          </div>
        )}

        {!loading && !error && series.length > 0 && (
          <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {series.map((s) => (
              <Link
                key={s.id}
                href={`/creator?series=${s.slug}`}
                className="card card-hover group"
              >
                {/* Cover */}
                <div className="aspect-[3/4] rounded-lg overflow-hidden bg-ink-800 mb-3">
                  {s.cover_url ? (
                    <img
                      src={s.cover_url}
                      alt={s.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-ink-600">
                      <svg
                        className="w-10 h-10"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.5}
                          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                        />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Info */}
                <h3 className="font-semibold text-sm text-ink-100 group-hover:text-sakura-400 transition-colors line-clamp-2">
                  {s.title}
                </h3>
                <p className="text-xs text-ink-400 mt-1">{s.author_name}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-sakura-500/10 text-sakura-400 border border-sakura-500/20">
                    {s.content_type}
                  </span>
                  {s.genres && (
                    <span className="text-[10px] text-ink-500 truncate">
                      {s.genres.split(",")[0]}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* ── Creator Spotlight ─────────────────────────── */}
      <section className="space-y-4">
        <h2 className="font-display text-xl font-bold sm:text-2xl">
          Creator Spotlight
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {series.slice(0, 3).map((s) => (
            <div key={`spotlight-${s.id}`} className="card">
              <p className="text-sm font-semibold text-sakura-400">
                {s.author_name}
              </p>
              <p className="text-xs text-ink-400 mt-1 line-clamp-2">
                {s.author_bio || `Creator of "${s.title}"`}
              </p>
              <Link
                href={`/creator?series=${s.slug}`}
                className="mt-2 inline-block text-xs text-sakura-300 hover:underline"
              >
                View work →
              </Link>
            </div>
          ))}
          {series.length === 0 && (
            <div className="card col-span-full text-center py-6">
              <p className="text-sm text-ink-400">
                Creators will be spotlighted here once originals are published.
              </p>
            </div>
          )}
        </div>
      </section>

      {/* ── Become a Creator CTA ──────────────────────── */}
      <section
        id="apply"
        className="card border-sakura-400/30 bg-gradient-to-br from-ink-900 to-sakura-950/30 p-6 sm:p-8 space-y-4"
      >
        <h2 className="font-display text-xl font-bold sm:text-2xl">
          Become a Nakama Creator
        </h2>
        <p className="text-sm text-ink-300 max-w-2xl">
          Have a story to tell? Join Nakama Originals and publish your comics
          and novels directly to thousands of readers. We handle hosting,
          discovery, and payments — you focus on creating.
        </p>
        <ul className="space-y-2 text-sm text-ink-300">
          <li className="flex items-start gap-2">
            <span className="text-sakura-400 mt-0.5">✦</span>
            <span>Publish comics and novels on your own terms</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-sakura-400 mt-0.5">✦</span>
            <span>Fair revenue share — you keep 70% of earnings</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-sakura-400 mt-0.5">✦</span>
            <span>Built-in discovery and reader analytics</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-sakura-400 mt-0.5">✦</span>
            <span>Simple approval process — get started in days</span>
          </li>
        </ul>
        <div className="flex flex-wrap gap-2 sm:gap-3 pt-2">
          <Link href="/creator" className="btn-primary">
            Apply Now
          </Link>
          <a href="#featured" className="btn-ghost">
            See Featured Work
          </a>
        </div>
      </section>

      {/* ── Stats ─────────────────────────────────────── */}
      <section className="grid gap-2 sm:gap-4 grid-cols-2 sm:grid-cols-4">
        <StatCard label="Published Series" value={series.length} />
        <StatCard label="Creator Revenue" value="70%" />
        <StatCard label="Content Types" value="2" />
        <StatCard label="Status" value="Live" />
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="card">
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-ink-50 tabular-nums sm:text-3xl">
        {value}
      </p>
    </div>
  );
}
