import { getJson } from "../../lib/api";
import { LiveHealthTicker } from "../../components/LiveHealthTicker";

export const runtime = "edge";

export const dynamic = "force-dynamic";

interface SourceHealth {
  name: string;
  kind: string;
  status: "healthy" | "degraded" | "down" | "unknown";
  ok: number;
  fail: number;
  success_rate: number;
  failure_streak: number;
  p50_ms: number | null;
}

interface HealthBoard {
  summary: { healthy: number; degraded: number; down: number; unknown: number; total: number };
  sources: SourceHealth[];
  stale_adapters: Array<{ name: string; age_days: number }>;
  auto_repair?: { enabled: boolean; open_breakers: string[]; stale_count: number };
}

interface Analytics {
  uptime_seconds: number;
  workers: number;
  requests: { last_60s: number };
  cost_guard: { load1: number; cores: number; alert: boolean };
  cache_backend?: { backend: string; size: number | string; max_size: number | string };
  search_latency?: { p50_ms: number; p95_ms: number; avg_ms: number; samples: number };
}

function statusColor(status: string): string {
  switch (status) {
    case "healthy":
      return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    case "degraded":
      return "bg-amber-500/20 text-amber-300 border-amber-500/30";
    case "down":
      return "bg-sakura-500/20 text-sakura-300 border-sakura-500/30";
    default:
      return "bg-ink-800 text-ink-300 border-ink-700";
  }
}

function statusTextColor(status: string): string {
  switch (status) {
    case "healthy":
      return "text-emerald-400";
    case "degraded":
      return "text-amber-400";
    case "down":
      return "text-sakura-400";
    default:
      return "text-ink-400";
  }
}

function formatUptime(s: number): string {
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  if (s < 86400) return `${(s / 3600).toFixed(1)}h`;
  return `${(s / 86400).toFixed(1)}d`;
}

export default async function DashboardPage() {
  let health: HealthBoard | null = null;
  let analytics: Analytics | null = null;
  let error: string | null = null;

  try {
    const [hb, ab] = await Promise.all([
      getJson<{ data: HealthBoard }>("/sources/health"),
      getJson<{ data: Analytics }>("/analytics"),
    ]);
    health = hb.data;
    analytics = ab.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold sm:text-3xl">Dashboard</h1>
        <div className="card text-sm text-sakura-200">{error}</div>
      </div>
    );
  }

  const summary = health?.summary ?? { healthy: 0, degraded: 0, down: 0, unknown: 0, total: 0 };
  const sources = health?.sources ?? [];
  const sourcesByKind: Record<string, SourceHealth[]> = {};
  for (const s of sources) {
    if (!sourcesByKind[s.kind]) sourcesByKind[s.kind] = [];
    sourcesByKind[s.kind].push(s);
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Dashboard</h1>
        <p className="text-sm text-ink-400">
          Real-time API health, source scoreboard, and traffic stats.
        </p>
      </header>

      {analytics ? (
        <section className="grid gap-2 grid-cols-2 sm:gap-3 lg:grid-cols-4">
          <MiniMetric
            label="Uptime"
            value={formatUptime(analytics.uptime_seconds)}
            sub={`${analytics.workers} workers`}
          />
          <MiniMetric
            label="Req / 60s"
            value={String(analytics.requests.last_60s)}
          />
          <MiniMetric
            label="Cache"
            value={String(analytics.cache_backend?.size ?? "?")}
            sub={String(analytics.cache_backend?.backend ?? "n/a")}
          />
          <MiniMetric
            label="CPU Load"
            value={analytics.cost_guard.load1.toFixed(1)}
            sub={`${analytics.cost_guard.cores} cores`}
            alert={analytics.cost_guard.alert}
          />
        </section>
      ) : null}

      {/* Live WS source health (client-side) */}
      <LiveHealthTicker />

      {/* Search latency + cache stats */}
      {analytics?.search_latency ? (
        <section className="grid gap-2 grid-cols-2 sm:gap-3 lg:grid-cols-4">
          {(() => {
            const sl = analytics!.search_latency!;
            const cb = analytics!.cache_backend;
            return (
              <>
                <MiniMetric
                  label="Search p50"
                  value={`${sl.p50_ms}ms`}
                  sub={`${sl.samples} samples`}
                />
                <MiniMetric
                  label="Search p95"
                  value={`${sl.p95_ms}ms`}
                  sub={`avg ${sl.avg_ms}ms`}
                />
                <MiniMetric
                  label="Cache backend"
                  value={String(cb?.backend ?? "memory")}
                />
                <MiniMetric
                  label="Max cache"
                  value={String(cb?.max_size ?? "?")}
                />
              </>
            );
          })()}
        </section>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-base font-semibold sm:text-lg">
          Source scoreboard
          <span className="ml-2 text-xs text-ink-400">
            {summary.healthy}/{summary.total} healthy
          </span>
        </h2>

        <div className="grid gap-2 grid-cols-2 sm:grid-cols-4 sm:gap-3">
          <MiniMetric
            label="Healthy"
            value={String(summary.healthy)}
            sub={summary.total > 0 ? `${Math.round((summary.healthy / summary.total) * 100)}%` : ""}
          />
          <MiniMetric
            label="Degraded"
            value={String(summary.degraded)}
            alert={summary.degraded > 0}
          />
          <MiniMetric
            label="Down"
            value={String(summary.down)}
            alert={summary.down > 0}
          />
          <MiniMetric
            label="Unknown"
            value={String(summary.unknown)}
          />
        </div>

        {Object.entries(sourcesByKind).map(([kind, items]) => (
          <div key={kind} className="space-y-1">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">
              {kind} ({items.length})
            </h3>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((s) => (
                <div
                  key={s.name}
                  className={`card flex items-center justify-between border ${statusColor(s.status)}`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`inline-block h-1.5 w-1.5 rounded-full ${statusTextColor(s.status).replace('text-', 'bg-')}`} />
                      <span className="truncate text-sm font-medium">{s.name}</span>
                    </div>
                    <p className="mt-0.5 text-[10px] text-ink-400 sm:text-xs">
                      ok={s.ok} fail={s.fail} ·{" "}
                      {s.p50_ms ? `${s.p50_ms}ms` : "n/a"}
                    </p>
                  </div>
                  <span className={`text-xs ${statusTextColor(s.status)}`}>{s.status}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      {health?.stale_adapters && health.stale_adapters.length > 0 ? (
        <section className="card border-amber-500/30 bg-amber-500/5 text-xs text-amber-200 sm:text-sm">
          <p className="font-semibold">Stale adapters (&gt;30d)</p>
          <ul className="mt-1 space-y-0.5">
            {health.stale_adapters.map((a) => (
              <li key={a.name}>
                {a.name} — {a.age_days}d old
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="card text-xs text-ink-400 sm:text-sm">
        <p>
          Live API:{" "}
          <a
            href="https://mynakama.web.id/docs"
            className="text-sakura-400 hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            API Docs
          </a>
        </p>
      </section>
    </div>
  );
}

function MiniMetric({
  label,
  value,
  sub,
  alert,
}: {
  label: string;
  value: string;
  sub?: string;
  alert?: boolean;
}) {
  return (
    <div className={`card ${alert ? "border-amber-500/40 bg-amber-500/5" : ""}`}>
      <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
      <p
        className={`mt-1 text-xl font-bold tabular-nums ${
          alert ? "text-amber-300" : "text-ink-50"
        } sm:text-2xl`}
      >
        {value}
      </p>
      {sub ? <p className="mt-0.5 text-xs text-ink-400">{sub}</p> : null}
    </div>
  );
}
