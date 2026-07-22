import Link from "next/link";
import { COMIC_SOURCES, fetchSourceHome } from "../../lib/api";
import { SourceGrid } from "../../components/SourceGrid";
import { SearchBox } from "../../components/SearchBox";
import { GridSkeleton } from "../../components/Skeleton";

export const runtime = "edge";
export const dynamic = "force-dynamic";

export default async function ComicPage({
  searchParams,
}: {
  searchParams?: { source?: string };
}) {
  const source = searchParams?.source || COMIC_SOURCES[0];

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Comics</h1>
        <p className="text-sm text-ink-400">
          Home listings from {COMIC_SOURCES.length} comic sources.
        </p>
      </header>

      <SearchBox kind="comic" source={source} placeholder={`Search ${source}...`} />

      <div className="flex flex-wrap gap-1.5 sm:gap-2">
        {COMIC_SOURCES.map((s) => (
          <Link
            key={s}
            href={`/comic?source=${s}`}
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

      <ComicContent source={source} />
    </div>
  );
}

async function ComicContent({ source }: { source: string }) {
  let items: unknown[] = [];
  let error: string | null = null;
  try {
    items = await fetchSourceHome("comic", source);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return <div className="card text-sm text-sakura-200">{error}</div>;
  }
  if (items.length === 0) {
    return <GridSkeleton count={8} />;
  }
  return <SourceGrid items={items as never[]} empty={`No home items from ${source}.`} source={source} kind="comic" />;
}
