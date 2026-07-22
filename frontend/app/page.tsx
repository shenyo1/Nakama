import Link from "next/link";
import { ANIME_SOURCES, COMIC_SOURCES, NOVEL_SOURCES, fetchStats } from "../lib/api";

export const runtime = "edge";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let stats: Awaited<ReturnType<typeof fetchStats>> | null = null;
  let error: string | null = null;
  try {
    stats = await fetchStats();
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  const totalSources = stats?.total_sources ?? ANIME_SOURCES.length + COMIC_SOURCES.length + NOVEL_SOURCES.length;
  const animeCount = stats?.source_counts?.anime ?? ANIME_SOURCES.length;
  const comicCount = stats?.source_counts?.comic ?? COMIC_SOURCES.length;
  const novelCount = stats?.source_counts?.novel ?? NOVEL_SOURCES.length;

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
          Nakama aggregates {totalSources} public sources ({animeCount} anime, {comicCount} comic, {novelCount} novel) behind
          a consistent JSON interface. Multi-source search with automatic
          deduplication, offline fixtures, WebSocket live updates, auto-repair
          circuit breakers, and a generated TypeScript SDK.
        </p>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <Link href="/anime" className="btn-primary">
            Anime
          </Link>
          <Link href="/comic" className="btn-primary">
            Comics
          </Link>
          <Link href="/novel" className="btn-primary">
            Novels
          </Link>
          <Link href="/search" className="btn-ghost">
            Cross-source search
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="grid gap-2 sm:gap-4 grid-cols-2 sm:grid-cols-4">
        <StatCard label="Total sources" value={totalSources} />
        <StatCard
          label="Anime sources"
          value={animeCount}
        />
        <StatCard
          label="Comic sources"
          value={comicCount}
        />
        <StatCard
          label="Novel sources"
          value={novelCount}
        />
      </section>

      {error ? (
        <div className="card border-sakura-500/40 text-sm text-sakura-200">
          Backend unreachable: <code className="text-xs">{error}</code>
        </div>
      ) : null}

      {/* Source lists */}
      <section className="space-y-3 sm:space-y-4">
        <h2 className="text-lg font-semibold sm:text-xl">Registered sources</h2>
        <div className="grid gap-2 sm:gap-4 md:grid-cols-3">
          <SourceList
            title="Anime"
            subtitle={`${animeCount} sources`}
            items={[...ANIME_SOURCES]}
            href="/anime"
          />
          <SourceList
            title="Comic"
            subtitle={`${comicCount} sources`}
            items={[...COMIC_SOURCES]}
            href="/comic"
          />
          <SourceList
            title="Novel"
            subtitle={`${novelCount} sources`}
            items={[...NOVEL_SOURCES]}
            href="/novel"
          />
        </div>
      </section>

      {/* Feature highlights */}
      <section className="grid gap-3 sm:gap-6 md:grid-cols-2">
        <FeatureCard
          title="Multi-source search"
          description={`Search across all ${comicCount} comic, ${animeCount} anime, or ${novelCount} novel sources at once. Results are deduplicated and ranked by coverage.`}
          href="/search"
        />
        <FeatureCard
          title="Auto-repair and resilience"
          description="Circuit breakers, domain rotation, proxy pools, DNS watchdog, and auto-restart keep sources healthy 24/7."
          href="/status"
        />
        <FeatureCard
          title="Offline-first testing"
          description="271 tests run without network. HTML fixtures capture real responses for deterministic CI. Add a source, save its fixture, ship with confidence."
          href="/status"
        />
        <FeatureCard
          title="TypeScript SDK"
          description="Generated from OpenAPI schema. 52 endpoints, 19 schemas. Drop it into any frontend project."
        />
      </section>

      {/* Footer links */}
      <section className="border-t border-ink-800 pt-4 text-sm text-ink-400 space-y-1 sm:pt-6">
        <p>
          <a
            href="https://github.com/afifghaffarr-source/Nakama"
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

function SourceList({
  title,
  subtitle,
  items,
  href,
}: {
  title: string;
  subtitle: string;
  items: string[];
  href: string;
}) {
  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm sm:text-base">{title}</h3>
          <p className="text-xs text-ink-400">{subtitle}</p>
        </div>
        <Link
          href={href}
          className="text-xs text-sakura-400 hover:underline shrink-0"
        >
          browse
        </Link>
      </div>
      <ul className="space-y-1 text-sm text-ink-300">
        {items.map((s) => (
          <li key={s} className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-neon-500 shrink-0" />
            {s}
          </li>
        ))}
      </ul>
    </div>
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
