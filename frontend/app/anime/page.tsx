import Link from "next/link";
import { ANIME_SOURCES, fetchSourceHome, fetchUnifiedHome } from "../../lib/api";
import { SourceGrid } from "../../components/SourceGrid";
import { UnifiedGrid } from "../../components/UnifiedGrid";
import { SearchBox } from "../../components/SearchBox";
import { GridSkeleton } from "../../components/Skeleton";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export default async function AnimePage({
  searchParams,
}: {
  searchParams?: { source?: string };
}) {
  // No ?source= in the URL => unified feed (providers hidden, deduplicated
  // across all sources). Passing ?source=otakudesu (e.g. from a bookmark or
  // the "browse by source" link at the bottom) still works as before.
  const source = searchParams?.source;

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Anime</h1>
        <p className="text-sm text-ink-400">
          {source
            ? `Home listings from ${source}.`
            : `Unified feed from ${ANIME_SOURCES.length} sources, deduplicated.`}
        </p>
      </header>

      <SearchBox kind="anime" source={source || ANIME_SOURCES[0]} placeholder="Search anime..." />

      {source ? (
        <>
          <div className="flex flex-wrap gap-1.5 sm:gap-2">
            <Link
              href="/anime"
              className="whitespace-nowrap rounded-full bg-ink-800 px-2.5 py-1 text-xs text-ink-200 hover:bg-ink-700 sm:px-3 sm:text-sm"
            >
              ← Unified feed
            </Link>
            {ANIME_SOURCES.map((s) => (
              <Link
                key={s}
                href={`/anime?source=${s}`}
                className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs sm:px-3 sm:text-sm ${
                  s === source
                    ? "bg-sakura-500 text-white"
                    : "bg-ink-800 text-ink-200 hover:bg-ink-700"
                }`}
              >
                {s}
              </Link>
            ))}
          </div>
          <AnimeContent source={source} />
        </>
      ) : (
        <>
          <UnifiedAnimeContent />
          <details className="text-xs text-ink-400">
            <summary className="cursor-pointer select-none hover:text-ink-200">
              Browse by source instead
            </summary>
            <div className="mt-2 flex flex-wrap gap-1.5 sm:gap-2">
              {ANIME_SOURCES.map((s) => (
                <Link
                  key={s}
                  href={`/anime?source=${s}`}
                  className="whitespace-nowrap rounded-full bg-ink-800 px-2.5 py-1 text-xs text-ink-200 hover:bg-ink-700 sm:px-3 sm:text-sm"
                >
                  {s}
                </Link>
              ))}
            </div>
          </details>
        </>
      )}
    </div>
  );
}

async function UnifiedAnimeContent() {
  try {
    const items = await fetchUnifiedHome("anime");
    if (items.length === 0) return <GridSkeleton count={8} />;
    return <UnifiedGrid items={items} empty="No home items available." kind="anime" />;
  } catch (e) {
    // Aggregate endpoint failed (e.g. all sources down) — fall back to the
    // first single source so the page still shows something.
    const message = e instanceof Error ? e.message : String(e);
    return (
      <div className="space-y-3">
        <div className="card text-sm text-sakura-200">
          Unified feed unavailable ({message}). Showing {ANIME_SOURCES[0]} instead.
        </div>
        <AnimeContent source={ANIME_SOURCES[0]} />
      </div>
    );
  }
}

async function AnimeContent({ source }: { source: string }) {
  let items: unknown[] = [];
  let error: string | null = null;
  try {
    items = await fetchSourceHome("anime", source);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return <div className="card text-sm text-sakura-200">{error}</div>;
  }
  if (items.length === 0) {
    return <GridSkeleton count={8} />;
  }
  return <SourceGrid items={items as never[]} empty={`No home items from ${source}.`} source={source} kind="anime" />;
}
