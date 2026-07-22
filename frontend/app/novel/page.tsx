import Link from "next/link";
import { NOVEL_SOURCES, fetchSourceHome } from "../../lib/api";
import { SourceGrid } from "../../components/SourceGrid";

export const runtime = "edge";

export const dynamic = "force-dynamic";

export default async function NovelPage({
  searchParams,
}: {
  searchParams?: { source?: string };
}) {
  const source = searchParams?.source || NOVEL_SOURCES[0];
  let items: unknown[] = [];
  let error: string | null = null;
  try {
    items = await fetchSourceHome("novel", source);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="space-y-1 sm:space-y-2">
        <h1 className="text-2xl font-bold sm:text-3xl">Novels</h1>
        <p className="text-sm text-ink-400">
          Home listings from {NOVEL_SOURCES.length} novel sources.
        </p>
      </header>

      <div className="flex flex-wrap gap-1.5 sm:gap-2">
        {NOVEL_SOURCES.map((s) => (
          <Link
            key={s}
            href={`/novel?source=${s}`}
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

      {error ? (
        <div className="card text-sm text-sakura-200">{error}</div>
      ) : (
        <SourceGrid items={items as never[]} empty={`No home items from ${source}.`} />
      )}
    </div>
  );
}
