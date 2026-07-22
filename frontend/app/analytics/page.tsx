import Link from "next/link";
import { ANIME_SOURCES, COMIC_SOURCES, NOVEL_SOURCES } from "../../lib/api";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export default function AnalyticsPage() {
  const totalSources = ANIME_SOURCES.length + COMIC_SOURCES.length + NOVEL_SOURCES.length;

  return (
    <div className="space-y-6 sm:space-y-8">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Analytics</h1>
        <p className="text-sm text-ink-400">
          Runtime metrics and monitoring. View raw JSON or check source health.
        </p>
      </header>

      <section className="grid gap-2 grid-cols-1 sm:gap-4 sm:grid-cols-2">
        <Link
          href="https://mynakama.web.id/analytics"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1 text-sm sm:text-base">Raw Analytics JSON</h2>
          <p className="text-xs text-ink-400 sm:text-sm">
            Uptime, requests, memory, CPU load, search latency, cache stats, quota tiers.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>

        <Link
          href="https://mynakama.web.id/analytics/search"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1 text-sm sm:text-base">Search Analytics JSON</h2>
          <p className="text-xs text-ink-400 sm:text-sm">
            Per-kind search latency breakdown (p50, p95, avg), slowest queries.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>

        <Link
          href="https://mynakama.web.id/sources/health"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1 text-sm sm:text-base">Source Health JSON</h2>
          <p className="text-xs text-ink-400 sm:text-sm">
            {totalSources} sources with status, circuit breakers, stale adapters, latency.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>

        <Link
          href="https://mynakama.web.id/docs"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1 text-sm sm:text-base">API Docs</h2>
          <p className="text-xs text-ink-400 sm:text-sm">
            OpenAPI/Swagger documentation for all endpoints.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>
      </section>

      <section className="card space-y-3">
        <h2 className="font-semibold text-sm sm:text-base">Quick Stats</h2>
        <div className="grid gap-2 grid-cols-2 sm:gap-3 sm:grid-cols-3 text-sm">
          <div>
            <span className="text-ink-400">Sources:</span>{" "}
            <span className="text-ink-200">{totalSources} ({ANIME_SOURCES.length} anime, {COMIC_SOURCES.length} comic, {NOVEL_SOURCES.length} novel)</span>
          </div>
          <div>
            <span className="text-ink-400">Tests:</span>{" "}
            <span className="text-ink-200">271 offline + 17 network</span>
          </div>
          <div>
            <span className="text-ink-400">Resilience:</span>{" "}
            <span className="text-ink-200">8 layers active</span>
          </div>
          <div>
            <span className="text-ink-400">API:</span>{" "}
            <span className="text-ink-200">FastAPI + Docker + CF</span>
          </div>
          <div>
            <span className="text-ink-400">Frontend:</span>{" "}
            <span className="text-ink-200">Next.js on CF Pages</span>
          </div>
          <div>
            <span className="text-ink-400">Auth:</span>{" "}
            <span className="text-ink-200">JWT + API Key + Burst</span>
          </div>
        </div>
      </section>

      <section className="card space-y-3">
        <h2 className="font-semibold text-sm sm:text-base">Quota Tiers</h2>
        <div className="grid gap-2 grid-cols-3 sm:gap-3">
          {[
            { plan: "free", limit: 1000, burst: "30/60s" },
            { plan: "pro", limit: 10000, burst: "200/60s" },
            { plan: "unlimited", limit: 0, burst: "1000/60s" },
          ].map(({ plan, limit, burst }) => (
            <div
              key={plan}
              className="rounded-lg border border-ink-700/60 p-2 sm:p-3"
            >
              <p className="text-xs uppercase tracking-wide text-ink-400">
                {plan}
              </p>
              <p className="mt-1 text-xl font-bold text-ink-50 tabular-nums sm:text-2xl">
                {limit === 0 ? "∞" : limit.toLocaleString()}
              </p>
              <p className="text-xs text-ink-400">requests/day</p>
              <p className="mt-1 text-xs text-ink-500">burst: {burst}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
