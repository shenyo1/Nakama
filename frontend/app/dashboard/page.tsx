import { getJson } from "../../lib/api";

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
  last_error: string | null;
  meta: {
    version: string;
    verified_on: string;
    notes: string;
  } | null;
}

interface HealthBoard {
  summary: { healthy: number; degraded: number; down: number; unknown: number; total: number };
  sources: SourceHealth[];
  auto_repair?: { enabled: boolean; open_breakers: string[] };
  stale_adapters?: { name: string; age_days: number }[];
}

interface Analytics {
  uptime_seconds: number;
  workers: number;
  requests: { last_60s: number; last_5m: number };
  memory: { VmSize: string; VmRSS: string };
  cost_guard: { load1: number; cores: number; load_ratio: number; alert: boolean };
  search_latency?: {
    samples: number;
    p50_ms: number;
    p95_ms: number;
    avg_ms: number;
  };
  source_latency?: Record<string, { p50_ms: number; p95_ms: number; avg_ms: number; samples: number }>;
  cache_backend?: { backend: string; size: number; max_size: number };
}

function statusColor(status: string): string {
  switch (status) {
    case "healthy": return "bg-neon-500";
    case "degraded": return "bg-amber-500";
    case "down": return "bg-sakura-500";
    default: return "bg-ink-600";
  }
}

function statusTextColor(status: string): string {
  switch (status) {
    case "healthy": return "text-neon-400";
    case "degraded": return "text-amber-300";
    case "down": return "text-sakura-300";
    default: return "text-ink-400";
  }
}

function formatUptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default async function DashboardPage() {
  let health: HealthBoard | null = null;
  let analytics: Analytics | null = null;
  let error: string | null = null;

  try {
    const [h, a] = await Promise.all([
      getJson("/sources/health") as Promise<{ data: HealthBoard }>,
      getJson("/analytics") as Promise<{ data: Analytics }>,
    ]);
    health = (h as { data: HealthBoard }).data;
    analytics = (a as { data: Analytics }).data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  const sources = health?.sources || [];
  const summary = health?.summary;
  const totalSources = summary?.total ?? sources.length;

  return (
    <div className="space-y-6 sm:space-y-8">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Dashboard</h1>
        <p className="text-sm text-ink-400">
          Real-time monitoring for {totalSources} sources across anime, comic, and novel providers.
        </p>
      </header>

      {error ? (
        <div className="card border-sakura-500/40 text-sm text-sakura-200">
          Failed to load: {error}
        </div>
      ) : null}

      {/* Summary row */}
      {summary ? (
        <section className="grid gap-2 grid-cols-2 sm:gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {([
            ["Total", summary.total, "text-ink-50"],
            ["Healthy", summary.healthy, "text-neon-400"],
            ["Degraded", summary.degraded, "text-amber-300"],
            ["Down", summary.down, "text-sakura-300"],
            ["Unknown", summary.unknown, "text-ink-300"],
          ] as const).map(([label, value, color]) => (
            <div key={label} className="card">
              <p className="text-xs uppercase tracking-wide text-ink-400">{label}</p>
              <p className={`mt-1 text-2xl font-bold tabular-nums ${color} sm:text-3xl`}>{value}</p>
            </div>
          ))}
        </section>
      ) : null}

      {/* Runtime metrics */}
      {analytics ? (
        <section className="grid gap-2 grid-cols-2 sm:gap-3 lg:grid-cols-4">
          <MiniMetric
            label="Uptime"
            value={formatUptime(analytics.uptime_seconds)}
            sub={`${analytics.workers} workers`}
          />
          <MiniMetric
            label="Requests (60s)"
            value={String(analytics.requests.last_60s)}
            sub={`${analytics.requests.last_5m} in 5min`}
          />
          <MiniMetric
            label="Memory RSS"
            value={analytics.memory.VmRSS.replace(" kB", " MB").replace(/(\d+)/, (m) => String(Math.round(Number(m) / 1024)))}
            sub={analytics.memory.VmSize.replace(" kB", " GB").replace(/(\d+)/, (m) => (Number(m) / 1048576).toFixed(1)) + " total"}
          />
          <MiniMetric
            label="CPU Load"
            value={analytics.cost_guard.load1.toFixed(1)}
            sub={`${analytics.cost_guard.cores} cores`}
            alert={analytics.cost_guard.alert}
          />
        </section>
      ) : null}

      {/* Search latency + cache stats */}
      {analytics?.search_latency || analytics?.cache_backend ? (
        <section className="grid gap-2 grid-cols-2 sm:gap-3 lg:grid-cols-4">
          {analytics.search_latency ? (
            <>
              <MiniMetric
                label="Search p50"
                value={`${analytics.search_latency.p50_ms}ms`}
                sub={`${analytics.search_latency.samples} samples`}
              />
              <MiniMetric
                label="Search p95"
                value={`${analytics.search_latency.p95_ms}ms`}
                sub={`avg ${analytics.search_latency.avg_ms}ms`}
              />
            </>
          ) : null}
          {analytics.cache_backend ? (
            <MiniMetric
              label="Cache"
              value={String(analytics.cache_backend.size)}
              sub={`${analytics.cache_backend.backend}`}
            />
          ) : null}
        </section>
      ) : null}

      {/* Auto-repair status */}
      {health?.auto_repair ? (
        <section className="card">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-sm sm:text-base">Auto-Repair</h2>
              <p className="text-xs text-ink-400 mt-0.5">
                {health.auto_repair.enabled ? "Enabled" : "Disabled"}
                {health.auto_repair.open_breakers?.length ? ` · ${health.auto_repair.open_breakers.length} breaker(s) open` : ""}
                {health.stale_adapters?.length ? ` · ${health.stale_adapters.length} stale adapter(s)` : ""}
              </p>
            </div>
            <span className={`inline-flex h-2 w-2 rounded-full ${health.auto_repair.enabled ? "bg-neon-500" : "bg-ink-600"}`} />
          </div>
          {health.auto_repair.open_breakers?.length ? (
            <p className="mt-2 text-xs text-sakura-300">
              Open: {health.auto_repair.open_breakers.join(", ")}
            </p>
          ) : null}
          {health.stale_adapters?.length ? (
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {health.stale_adapters.map((s) => (
                <span key={s.name} className="rounded bg-amber-500/10 px-2 py-0.5 text-amber-300">
                  {s.name} ({s.age_days}d)
                </span>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {/* Source grid */}
      <section className="space-y-2 sm:space-y-3">
        <h2 className="text-lg font-semibold sm:text-xl">Sources</h2>
        <div className="grid gap-2 grid-cols-1 sm:gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {sources.map((s) => (
            <div
              key={s.name}
              className={`card border-l-2 ${
                s.status === "healthy"
                  ? "border-l-neon-500"
                  : s.status === "degraded"
                    ? "border-l-amber-500"
                    : s.status === "down"
                      ? "border-l-sakura-500"
                      : "border-l-ink-600"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm truncate">{s.name}</h3>
                <span className={`inline-flex h-2 w-2 rounded-full shrink-0 ${statusColor(s.status)}`} />
              </div>

              {/* Success rate bar */}
              <div className="mb-2">
                <div className="flex justify-between text-xs text-ink-400 mb-1">
                  <span>Success rate</span>
                  <span className="tabular-nums">{Math.round(s.success_rate * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-ink-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      s.success_rate >= 0.9 ? "bg-neon-500" : s.success_rate >= 0.5 ? "bg-amber-500" : "bg-sakura-500"
                    }`}
                    style={{ width: `${Math.round(s.success_rate * 100)}%` }}
                  />
                </div>
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-3 gap-1 text-xs mb-2">
                <div>
                  <span className="text-ink-400">OK</span>
                  <span className="ml-1 text-ink-200 tabular-nums">{s.ok}</span>
                </div>
                <div>
                  <span className="text-ink-400">Fail</span>
                  <span className="ml-1 text-ink-200 tabular-nums">{s.fail}</span>
                </div>
                <div>
                  <span className="text-ink-400">Streak</span>
                  <span className={`ml-1 tabular-nums ${s.failure_streak > 0 ? "text-sakura-300" : "text-ink-200"}`}>
                    {s.failure_streak}
                  </span>
                </div>
              </div>

              {/* Latency + kind */}
              <div className="flex justify-between text-xs text-ink-400">
                <span>{s.kind}</span>
                {s.p50_ms != null ? (
                  <span className="tabular-nums">{s.p50_ms}ms p50</span>
                ) : null}
              </div>

              {/* Error */}
              {s.last_error ? (
                <p className="mt-2 text-xs text-sakura-300 truncate" title={s.last_error}>
                  {s.last_error}
                </p>
              ) : null}

              {/* Meta */}
              {s.meta?.verified_on ? (
                <p className="mt-2 text-xs text-ink-500">
                  v{s.meta.version} · verified {s.meta.verified_on}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <section className="border-t border-ink-800 pt-4 text-sm text-ink-400 space-y-1 sm:pt-6">
        <p className="text-xs sm:text-sm">
          <a href="https://mynakama.web.id/sources/health" className="text-sakura-400 hover:underline" target="_blank" rel="noreferrer">
            Health JSON
          </a>
          {" · "}
          <a href="https://mynakama.web.id/analytics" className="text-sakura-400 hover:underline" target="_blank" rel="noreferrer">
            Analytics JSON
          </a>
          {" · "}
          <a href="https://mynakama.web.id/analytics/search" className="text-sakura-400 hover:underline" target="_blank" rel="noreferrer">
            Search Analytics
          </a>
          {" · "}
          <a href="https://mynakama.web.id/stats" className="text-sakura-400 hover:underline" target="_blank" rel="noreferrer">
            Stats JSON
          </a>
          {" · "}
          <a href="https://mynakama.web.id/docs" className="text-sakura-400 hover:underline" target="_blank" rel="noreferrer">
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
      <p className={`mt-1 text-xl font-bold tabular-nums ${alert ? "text-amber-300" : "text-ink-50"} sm:text-2xl`}>
        {value}
      </p>
      {sub ? <p className="mt-0.5 text-xs text-ink-400">{sub}</p> : null}
    </div>
  );
}
