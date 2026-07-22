import Link from "next/link";
import { ANIME_SOURCES, fetchSourceHome } from "../../lib/api";
import { SourceGrid } from "../../components/SourceGrid";

export const runtime = "edge";

export const dynamic = "force-dynamic";

export default async function AnimePage({
  searchParams,
}: {
  searchParams?: { source?: string };
}) {
  const source = searchParams?.source || ANIME_SOURCES[0];
  let items: unknown[] = [];
  let error: string | null = null;
  try {
    items = await fetchSourceHome("anime", source);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Anime</h1>
        <p className="text-sm text-ink-400">
          Home listings from 6 anime sources.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {ANIME_SOURCES.map((s) => (
          <Link
            key={s}
            href={`/anime?source=${s}`}
            className={`rounded-full px-3 py-1 text-sm ${
              s === source
                ? "bg-sakura-500 text-white"
                : "bg-ink-800 text-ink-200 hover:bg-ink-700"
            }`}
          >
            {s}
          </Link>
        ))}
      </div>

      {error ? (
        <div className="card text-sm text-sakura-200">{error}</div>
      ) : (
        <SourceGrid items={items as never[]} empty={`No home items from ${source}.`} />
      )}
    </div>
  );
}
