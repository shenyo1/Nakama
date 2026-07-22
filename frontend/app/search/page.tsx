import { crossSearch } from "../../lib/api";
import type { ApiKind } from "../../lib/types";
import { SourceGrid } from "../../components/SourceGrid";

export const runtime = "edge";

export const dynamic = "force-dynamic";

export default async function SearchPage({
  searchParams,
}: {
  searchParams?: { q?: string; type?: string };
}) {
  const q = (searchParams?.q || "").trim();
  const type = ((searchParams?.type as ApiKind) || "comic") as ApiKind;
  let results: Awaited<ReturnType<typeof crossSearch>> | null = null;
  let error: string | null = null;

  if (q) {
    try {
      results = await crossSearch(q, type);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  const flatItems =
    results && results.results
      ? Object.entries(results.results).flatMap(([source, items]) =>
          (items || []).slice(0, 8).map((it) => ({
            ...(it as object),
            badge: source,
          }))
        )
      : [];

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Cross-source search</h1>
        <p className="text-sm text-ink-400">
          Hits every registered source of the selected type.
        </p>
      </header>

      <form className="card flex flex-col gap-3 sm:flex-row sm:items-end" method="get">
        <label className="flex-1 text-sm">
          <span className="mb-1 block text-ink-400">Query</span>
          <input
            name="q"
            defaultValue={q}
            placeholder="e.g. one piece, boruto, isekai"
            className="w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-ink-50"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-ink-400">Type</span>
          <select
            name="type"
            defaultValue={type}
            className="rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-ink-50"
          >
            <option value="comic">comic</option>
            <option value="anime">anime</option>
            <option value="novel">novel</option>
          </select>
        </label>
        <button type="submit" className="btn-primary">
          Search
        </button>
      </form>

      {error ? <div className="card text-sm text-sakura-200">{error}</div> : null}

      {results ? (
        <div className="space-y-3 text-sm text-ink-400">
          <p>
            Tried: {(results.sources_tried || []).join(", ") || "—"} · Failed:{" "}
            {(results.sources_failed || []).length}
          </p>
          <SourceGrid items={flatItems as never[]} empty="No matches." />
        </div>
      ) : !q ? (
        <div className="card text-sm text-ink-400">Enter a query to search.</div>
      ) : null}
    </div>
  );
}
