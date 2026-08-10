import { getJson, imageProxyUrl } from "../../../../../lib/api";
import { RecommendationWidget } from "../../../../../components/RecommendationWidget";
import { ClientCommunity } from "../../../../../components/ClientCommunity";
import ShareCard from "../../../../../components/ShareCard";
import Link from "next/link";
import { BackLink } from "../../../../../components/BackLink";

export const runtime = "edge";
export const dynamic = "force-dynamic";

interface NovelChapter {
  slug?: string;
  title?: string;
  chapter?: number | string;
  url?: string;
  [k: string]: unknown;
}

interface NovelDetail {
  title?: string;
  slug?: string;
  thumbnail?: string;
  cover?: string;
  synopsis?: string;
  author?: string;
  status?: string;
  type?: string;
  total_chapters?: number;
  genres?: string[];
  chapters?: NovelChapter[];
  [k: string]: unknown;
}

export default async function NovelDetailPage({
  params,
}: {
  params: { source: string; slug: string };
}) {
  const { source, slug } = params;
  let detail: NovelDetail | null = null;
  let error: string | null = null;

  try {
    const body = await getJson<{ data: NovelDetail }>(`/novel/${source}/detail/${slug}`);
    detail = body.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink href="/novel" label="Back to Novels" />
        <div className="card text-sm text-sakura-200">
          <p className="font-semibold mb-1">Novel not found</p>
          <p className="text-ink-400">{error}</p>
          <p className="text-xs text-ink-500 mt-2">
            Try{" "}
            <Link href="/novel" className="text-sakura-400 hover:underline">
              browsing novels
            </Link>{" "}
            or use{" "}
            <Link href="/search" className="text-sakura-400 hover:underline">
              search
            </Link>.
          </p>
        </div>
      </div>
    );
  }

  if (!detail) return null;

  // Detect empty detail (slug stale / source page missing)
  const isEmpty =
    !detail.title ||
    (!detail.synopsis && !detail.chapters?.length && !detail.thumbnail);

  if (isEmpty) {
    return (
      <div className="space-y-4">
        <BackLink href="/novel" label="Back to Novels" />
        <div className="card text-sm">
          <p className="font-semibold mb-1 text-sakura-200">No content available</p>
          <p className="text-ink-400">
            We could not load details for this novel. The source may have
            removed or moved this page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BackLink href="/novel" label="Back to Novels" />

      <div className="flex flex-col gap-4 sm:flex-row sm:gap-6">
        {(detail.thumbnail || detail.cover) ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageProxyUrl(detail.thumbnail || detail.cover || "")}
            alt={detail.title || "cover"}
            className="w-28 shrink-0 rounded-lg object-cover sm:w-36"
            loading="lazy"
          />
        ) : null}
        <div className="min-w-0 space-y-2">
          <h1 className="text-xl font-bold sm:text-2xl">{detail.title || slug}</h1>
          {detail.author ? <p className="text-sm text-ink-400">Author: {detail.author}</p> : null}
          {detail.status ? <p className="text-sm text-ink-400">Status: {detail.status}</p> : null}
          {detail.total_chapters ? <p className="text-sm text-ink-400">Chapters: {detail.total_chapters}</p> : null}
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

      {/* Share */}
      <ShareCard
        title={detail.title || slug}
        kind="novel"
        source={source}
        slug={slug}
        thumbnail={detail.thumbnail}
        description={detail.synopsis}
        genres={detail.genres}
        url={`https://api.mynakama.web.id/novel/${source}/detail/${slug}`}
      />

      {detail.chapters?.length ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold sm:text-base">Chapters ({detail.chapters.length})</h2>
          <div className="card divide-y divide-ink-800">
            {detail.chapters.slice(0, 80).map((ch, i) => (
              <Link
                key={ch.slug || ch.chapter || i}
                href={`/novel/${source}/chapter/${ch.slug || ch.chapter}`}
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

      {/* AI-Powered Recommendations */}
      <RecommendationWidget
        title={detail.title || slug}
        kind="novel"
        source={source}
        synopsis={detail.synopsis}
        genres={detail.genres}
      />

      {/* Community: Reviews & Comments */}
      <section className="space-y-6">
        <ClientCommunity source={source} slug={slug} kind="novel" />
      </section>
    </div>
  );
}
