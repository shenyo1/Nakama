import { getJson } from "../../../../../lib/api";
import { SourceGrid } from "../../../../../components/SourceGrid";
import Link from "next/link";

export const runtime = "edge";
export const dynamic = "force-dynamic";

interface Chapter {
  slug?: string;
  title?: string;
  chapter?: number | string;
  url?: string;
  [k: string]: unknown;
}

interface ComicDetail {
  title?: string;
  slug?: string;
  thumbnail?: string;
  synopsis?: string;
  author?: string;
  artist?: string;
  status?: string;
  type?: string;
  total_chapters?: number;
  genres?: string[];
  chapters?: Chapter[];
  [k: string]: unknown;
}

export default async function ComicMangaPage({
  params,
}: {
  params: { source: string; slug: string };
}) {
  const { source, slug } = params;
  let detail: ComicDetail | null = null;
  let error: string | null = null;

  try {
    const body = await getJson<{ data: ComicDetail }>(`/comic/${source}/manga/${slug}`);
    detail = body.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href="/comic" className="text-sm text-sakura-400 hover:underline">
          ← Back to Comics
        </Link>
        <div className="card text-sm text-sakura-200">{error}</div>
      </div>
    );
  }

  if (!detail) return null;

  return (
    <div className="space-y-6">
      <Link href="/comic" className="text-sm text-sakura-400 hover:underline">
        ← Back to Comics
      </Link>

      <div className="flex flex-col gap-4 sm:flex-row sm:gap-6">
        {detail.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`/api/backend/image?url=${encodeURIComponent(detail.thumbnail)}`}
            alt={detail.title || "cover"}
            className="w-32 shrink-0 rounded-lg object-cover sm:w-40"
            loading="lazy"
          />
        ) : null}
        <div className="min-w-0 space-y-2">
          <h1 className="text-xl font-bold sm:text-2xl">{detail.title || slug}</h1>
          {detail.author ? (
            <p className="text-sm text-ink-400">Author: {detail.author}</p>
          ) : null}
          {detail.status ? (
            <p className="text-sm text-ink-400">Status: {detail.status}</p>
          ) : null}
          {detail.total_chapters ? (
            <p className="text-sm text-ink-400">Chapters: {detail.total_chapters}</p>
          ) : null}
          {detail.genres?.length ? (
            <div className="flex flex-wrap gap-1.5">
              {detail.genres.slice(0, 10).map((g) => (
                <span key={g} className="badge">{g}</span>
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {detail.synopsis ? (
        <section className="card">
          <h2 className="mb-2 text-sm font-semibold sm:text-base">Synopsis</h2>
          <p className="text-sm text-ink-300 leading-relaxed">{detail.synopsis}</p>
        </section>
      ) : null}

      {detail.chapters?.length ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold sm:text-base">Chapters ({detail.chapters.length})</h2>
          <div className="card divide-y divide-ink-800">
            {detail.chapters.slice(0, 50).map((ch, i) => (
              <Link
                key={ch.slug || ch.chapter || i}
                href={`/comic/${source}/chapter/${ch.slug || ch.chapter}`}
                className="flex items-center justify-between py-2 text-sm hover:bg-ink-800/50 px-2 -mx-2 rounded"
              >
                <span className="truncate text-ink-200">
                  {ch.title || `Chapter ${ch.chapter || i + 1}`}
                </span>
                <span className="text-xs text-ink-400 shrink-0 ml-2">Read →</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
