import Link from "next/link";
import { fetchSourceHealth } from "../../lib/api";

export const dynamic = "force-dynamic";

function statusColor(status: string): string {
  switch (status) {
    case "healthy":
      return "text-neon-400 border-neon-400/40 bg-neon-400/10";
    case "degraded":
      return "text-amber-300 border-amber-400/40 bg-amber-400/10";
    case "down":
      return "text-sakura-300 border-sakura-400/40 bg-sakura-400/10";
    default:
      return "text-ink-300 border-ink-600 bg-ink-800/50";
  }
}

export default async function StatusPage({
  searchParams,
}: {
  searchParams?: { probe?: string };
}) {
  const probe = searchParams?.probe === "1" || searchParams?.probe === "true";
  let board: Awaited<ReturnType<typeof fetchSourceHealth>> | null = null;
  let error: string | null = null;
  try {
    board = await fetchSourceHealth(probe);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  const summary = board?.summary;
  const sources = board?.sources || [];
  const infra = board?.infra || {};

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-sakura-400">
          Operations
        </p>
        <h1 className="text-3xl font-bold sm:text-4xl">Source status</h1>
        <p className="max-w-2xl text-sm text-ink-400">
          Live scoreboard from{" "}
          <code className="text-neon-400">GET /sources/health</code>. Passiveive mode
          shows counters from recent traffic; probe mode actively hits each
          source&apos;s home listing.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/status"
            className={`btn-ghost ${!probe ? "ring-1 ring-sakura-400/50" : ""}`}
          >
            Passive
          </Link>
          <Link
            href="/status?probe=1"
            className={`btn-ghost ${probe ? "ring-1 ring-sakura-400/50" : ""}`}
          >
            Active probe
          </Link>
          <a
            href={`${process.env.NEXT_PUBLIC_API_BASE || "https://mynakama.web.id"}/sources/health${probe ? "?probe=true" : ""}`}
            className="btn-ghost"
            target="_blank"
            rel="noreferrer"
          >
            Raw JSON ↗
          </a>
        </div>
      </header>

      {error ? (
        <div className="card border-sakura-500/40 text-sm text-sakura-200">
          Failed to load health: <code className="text-xs">{error}</code>
        </div>
      ) : null}

      {summary ? (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {(
            [
              ["Total", summary.total, "text-ink-50"],
              ["Healthy", summary.healthy, "text-neon-400"],
              ["Degraded", summary.degraded, "text-amber-300"],
              ["Down", summary.down, "text-sakura-300"],
              ["Unknown", summary.unknown, "text-ink-300"],
            ] as const
          ).map(([label, value, color]) => (
            <div key={label} className="card">
              <p className="text-xs uppercase tracking-wide text-ink-400">
                {label}
              </p>
              <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </section>
      ) : null}

      {Object.keys(infra).length ? (
        <section className="card space-y-2 text-sm">
          <h2 className="font-semibold">Infra</h2>
          <dl className="grid gap-1 sm:grid-cols-2">
            {Object.entries(infra).map(([k, v]) => {
              let display: string;
              if (typeof v === "boolean") display = v ? "yes" : "no";
              else if (v && typeof v === "object" && "ok" in (v as object)) {
                const o = v as { ok?: boolean; status?: number | null; error?: string | null };
                display = o.ok
                  ? `up${o.status != null ? ` (HTTP ${o.status})` : ""}`
                  : `down${o.error ? `: ${o.error}` : ""}`;
              } else {
                display = String(v ?? "—");
              }
              return (
                <div key={k} className="flex gap-2">
                  <dt className="text-ink-400">{k}:</dt>
                  <dd className="truncate text-ink-100">{display}</dd>
                </div>
              );
            })}
          </dl>
          {infra.komikcast_appwrite_auth &&
          typeof infra.komikcast_appwrite_auth === "object" &&
          (infra.komikcast_appwrite_auth as { ok?: boolean }).ok === false ? (
            <p className="mt-2 text-xs text-sakura-300">
              Komikcast Appwrite auth host unreachable — chapter images cannot be
              enabled until their login backend is back (localStorage.token stays null).
            </p>
          ) : null}
        </section>
      ) : null}

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Sources</h2>
        <div className="overflow-x-auto rounded-xl border border-ink-700/60">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-ink-900/80 text-xs uppercase tracking-wide text-ink-400">
              <tr>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Kind</th>
                <th className="px-3 py-2">OK / Fail</th>
                <th className="px-3 py-2">p50 ms</th>
                <th className="px-3 py-2">Transport</th>
                <th className="px-3 py-2">Notes</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr
                  key={s.name}
                  className="border-t border-ink-800/80 hover:bg-ink-900/40"
                >
                  <td className="px-3 py-2 font-medium text-ink-50">{s.name}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold uppercase ${statusColor(
                        s.status
                      )}`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-ink-300">{s.kind}</td>
                  <td className="px-3 py-2 tabular-nums text-ink-200">
                    {s.ok} / {s.fail}
                    {s.success_rate != null ? (
                      <span className="ml-1 text-xs text-ink-400">
                        ({Math.round(s.success_rate * 100)}%)
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-ink-300">
                    {s.p50_ms ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-ink-300">{s.transport || "—"}</td>
                  <td className="max-w-xs px-3 py-2 text-xs text-ink-400">
                    {s.last_error ? (
                      <span className="text-sakura-300">{s.last_error}</span>
                    ) : (
                      <>
                        {s.notes || "—"}
                        {s.limitations && s.limitations.length ? (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {s.limitations.map((l) => (
                              <span key={l} className="badge">
                                {l}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {!sources.length && !error ? (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-ink-400">
                    No source data yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
        {probe ? (
          <p className="text-xs text-ink-500">
            Active probe mode may take 10–60s and can trip rate limits (e.g.
            Jikan). Prefer passive for dashboards.
          </p>
        ) : (
          <p className="text-xs text-ink-500">
            Passive mode reflects recent API traffic. Hit source endpoints or
            run an active probe to populate counters.
          </p>
        )}
      </section>
    </div>
  );
}
