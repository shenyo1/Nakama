import { getJson } from "../../../../../lib/api";
import { RecommendationWidget } from "../../../../../components/RecommendationWidget";
import { ClientCommunity } from "../../../../../components/ClientCommunity";
import ShareCard from "../../../../../components/ShareCard";
import Link from "next/link";
import { BackLink } from "../../../../../components/BackLink";

export const runtime = "edge";
export const dynamic = "force-dynamic";

interface Episode {
  slug?: string;
  title?: string;
  episode?: number | string;
  url?: string;
  [k: string]: unknown;
}

interface AnimeDetail {
  title?: string;
  slug?: string;
  thumbnail?: string;
  synopsis?: string;
  studio?: string;
  status?: string;
  type?: string;
  total_episodes?: number;
  score?: number | string;
  genres?: string[];
  episodes?: Episode[];
  [k: string]: unknown;
}

export default async function AnimeDetailPage({
  params,
}: {
  params: { source: string; slug: string };
}) {
  const { source, slug } = params;
  let detail: AnimeDetail | null = null;
  let error: string | null = null;

  try {
    const body = await getJson<{ data: AnimeDetail }>(`/anime/${source}/detail/${slug}`);
    detail = body.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink href="/anime" label="Back to Anime" />
        <div className="card text-sm text-sakura-200">
          <p className="font-semibold mb-1">Anime not found</p>
          <p className="text-ink-400">{error}</p>
          <p className="text-xs text-ink-500 mt-2">
            The slug may have changed on the source site. Try{" "}
            <Link href="/anime" className="text-sakura-400 hover:underline">
              browsing anime listings
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
    (!detail.synopsis && !detail.episodes?.length && !detail.thumbnail);

  if (isEmpty) {
    return (
      <div className="space-y-4">
        <BackLink href="/anime" label="Back to Anime" />
        <div className="card text-sm">
          <p className="font-semibold mb-1 text-sakura-200">No content available</p>
          <p className="text-ink-400">
            We could not load details for this anime. The source may have
            removed or moved this page.
          </p>
          <p className="text-xs text-ink-500 mt-2">
            Try{" "}
            <Link href="/anime" className="text-sakura-400 hover:underline">
              browsing anime listings
            </Link>{" "}
            or{" "}
            <Link href="/search" className="text-sakura-400 hover:underline">
              search
            </Link>{" "}
            for similar titles.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BackLink href="/anime" label="Back to Anime" />

      <div className="flex flex-col gap-4 sm:flex-row sm:gap-6">
        {detail.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`/image?url=${encodeURIComponent(detail.thumbnail)}`}
            alt={detail.title || "cover"}
            className="w-32 shrink-0 rounded-lg object-cover sm:w-40"
            loading="lazy"
          />
        ) : null}
        <div className="min-w-0 space-y-2">
          <h1 className="text-xl font-bold sm:text-2xl">{detail.title || slug}</h1>
          {detail.studio ? <p className="text-sm text-ink-400">Studio: {detail.studio}</p> : null}
          {detail.status ? <p className="text-sm text-ink-400">Status: {detail.status}</p> : null}
          {detail.total_episodes ? <p className="text-sm text-ink-400">Episodes: {detail.total_episodes}</p> : null}
          {detail.score ? <p className="text-sm text-ink-400">Score: {detail.score}</p> : null}
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
        kind="anime"
        source={source}
        slug={slug}
        thumbnail={detail.thumbnail}
        description={detail.synopsis}
        episodes={detail.total_episodes ? String(detail.total_episodes) : undefined}
        genres={detail.genres}
        url={`https://app.mynakama.web.id/anime/${source}/detail/${slug}`}
      />

      {detail.episodes?.length ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold sm:text-base">Episodes ({detail.episodes.length})</h2>
          <div className="card divide-y divide-ink-800">
            {detail.episodes.slice(0, 50).map((ep, i) => (
              <Link
                key={ep.slug || ep.episode || i}
                href={`/anime/${source}/episode/${ep.slug || ep.episode}`}
                className="flex items-center justify-between py-2 text-sm hover:bg-ink-800/50 px-2 -mx-2 rounded"
              >
                <span className="truncate text-ink-200">
                  {ep.title || `Episode ${ep.episode || i + 1}`}
                </span>
                <span className="text-xs text-ink-400 shrink-0 ml-2">Watch →</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      {/* AI-Powered Recommendations */}
      <RecommendationWidget
        title={detail.title || slug}
        kind="anime"
        source={source}
        synopsis={detail.synopsis}
        genres={detail.genres}
      />

      {/* Community: Reviews & Comments */}
      <section className="space-y-6">
        <ClientCommunity source={source} slug={slug} kind="anime" />
      </section>
    </div>
  );
}
