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

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sakura-400">
          Multi-source aggregation
        </p>
        <h1 className="max-w-3xl font-display text-4xl font-bold leading-tight sm:text-5xl">
          Browse anime, comics & novels from{" "}
          <span className="text-sakura-400">10 sources</span> through one API.
        </h1>
        <p className="max-w-2xl text-ink-300">
          This demo frontend talks to the Nakama FastAPI backend —
          offline fixtures, image proxy, WebSocket chapter updates, Prometheus
          metrics, and a generated TypeScript SDK.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/anime" className="btn-primary">
            Explore Anime
          </Link>
          <Link href="/comic" className="btn-ghost">
            Explore Comics
          </Link>
          <Link href="/ws-test" className="btn-ghost">
            Live WebSocket
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total sources" value={stats?.total_sources ?? "—"} />
        <StatCard label="Anime sources" value={stats?.source_counts?.anime ?? ANIME_SOURCES.length} />
        <StatCard label="Comic sources" value={stats?.source_counts?.comic ?? COMIC_SOURCES.length} />
        <StatCard label="Novel sources" value={stats?.source_counts?.novel ?? NOVEL_SOURCES.length} />
      </section>

      {error ? (
        <div className="card border-sakura-500/40 text-sm text-sakura-200">
          Backend unreachable: <code className="text-xs">{error}</code>
          <p className="mt-2 text-ink-400">
            Start the API:{" "}
            <code className="text-neon-400">
              uvicorn app.main:app --port 8000
            </code>
          </p>
        </div>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Registered sources</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <SourceList title="Anime" items={[...ANIME_SOURCES]} href="/anime" />
          <SourceList title="Comic" items={[...COMIC_SOURCES]} href="/comic" />
          <SourceList title="Novel" items={[...NOVEL_SOURCES]} href="/novel" />
        </div>
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card">
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p className="mt-1 text-3xl font-bold text-ink-50">{value}</p>
    </div>
  );
}

function SourceList({
  title,
  items,
  href,
}: {
  title: string;
  items: string[];
  href: string;
}) {
  return (
    <div className="card">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold">{title}</h3>
        <Link href={href} className="text-xs text-sakura-400 hover:underline">
          open →
        </Link>
      </div>
      <ul className="space-y-1 text-sm text-ink-300">
        {items.map((s) => (
          <li key={s} className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-neon-500" />
            {s}
          </li>
        ))}
      </ul>
    </div>
  );
}
