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
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold">Novels</h1>
        <p className="text-sm text-ink-400">
          5 novel sources: Sakuranovel, Novelbin, Novelfull, Meionovels, Novelhub.
          offline fixtures work in CI.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {NOVEL_SOURCES.map((s) => (
          <Link
            key={s}
            href={`/novel?source=${s}`}
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
