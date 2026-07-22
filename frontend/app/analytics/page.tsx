import Link from "next/link";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export default function AnalyticsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Analytics</h1>
        <p className="text-sm text-ink-400">
          Runtime metrics and monitoring. View raw JSON or check source health.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <Link
          href="https://mynakama.web.id/analytics"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1">Raw Analytics JSON</h2>
          <p className="text-sm text-ink-400">
            Uptime, requests, memory, CPU load, cache policy, quota tiers.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>

        <Link
          href="https://mynakama.web.id/sources/health"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1">Source Health JSON</h2>
          <p className="text-sm text-ink-400">
            20 sources with status, circuit breakers, stale adapters, latency.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>

        <Link
          href="https://mynakama.web.id/stats"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1">Stats JSON</h2>
          <p className="text-sm text-ink-400">
            Source counts, uptime, offline mode status.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>

        <Link
          href="https://mynakama.web.id/docs"
          target="_blank"
          rel="noreferrer"
          className="card card-hover"
        >
          <h2 className="font-semibold mb-1">API Docs</h2>
          <p className="text-sm text-ink-400">
            OpenAPI/Swagger documentation for all endpoints.
          </p>
          <p className="mt-2 text-xs text-sakura-400">Open in new tab</p>
        </Link>
      </section>

      <section className="card space-y-3">
        <h2 className="font-semibold">Quick Stats</h2>
        <div className="grid gap-3 sm:grid-cols-3 text-sm">
          <div>
            <span className="text-ink-400">Sources:</span>{" "}
            <span className="text-ink-200">20 (6 anime, 9 comic, 5 novel)</span>
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
            <span className="text-ink-200">FastAPI + Docker + Cloudflare</span>
          </div>
          <div>
            <span className="text-ink-400">Frontend:</span>{" "}
            <span className="text-ink-200">Next.js on CF Pages</span>
          </div>
          <div>
            <span className="text-ink-400">Auth:</span>{" "}
            <span className="text-ink-200">JWT + API Key</span>
          </div>
        </div>
      </section>

      <section className="card space-y-3">
        <h2 className="font-semibold">Quota Tiers</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {[
            { plan: "free", limit: 1000 },
            { plan: "pro", limit: 10000 },
            { plan: "unlimited", limit: 0 },
          ].map(({ plan, limit }) => (
            <div
              key={plan}
              className="rounded-lg border border-ink-700/60 p-3"
            >
              <p className="text-xs uppercase tracking-wide text-ink-400">
                {plan}
              </p>
              <p className="mt-1 text-2xl font-bold text-ink-50 tabular-nums">
                {limit === 0 ? "∞" : limit.toLocaleString()}
              </p>
              <p className="text-xs text-ink-400">requests/day</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
