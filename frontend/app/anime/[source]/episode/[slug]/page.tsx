import { getJson } from "../../../../../lib/api";
import { ClientComments } from "../../../../../components/ClientComments";
import Link from "next/link";
import { BackLink } from "../../../../../components/BackLink";
import VideoPlayer from "../../../../../components/VideoPlayer";

export const runtime = "edge";
export const dynamic = "force-dynamic";

interface EpisodeStream {
  url?: string;
  quality?: string;
  host?: string;
  type?: string;
  [k: string]: unknown;
}

interface EpisodeDetail {
  title?: string;
  slug?: string;
  streams?: EpisodeStream[];
  download_links?: EpisodeStream[];
  episode?: number | string;
  [k: string]: unknown;
}

export default async function AnimeEpisodePage({
  params,
}: {
  params: { source: string; slug: string };
}) {
  const { source, slug } = params;
  let episode: EpisodeDetail | null = null;
  let error: string | null = null;

  try {
    const body = await getJson<{ data: EpisodeDetail }>(`/anime/${source}/episode/${slug}`);
    episode = body.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink href="/anime" label="Back" />
        <div className="card text-sm text-sakura-200">
          <p className="font-semibold mb-1">Episode not found</p>
          <p className="text-ink-400">{error}</p>
          <p className="text-xs text-ink-500 mt-2">
            The source may have moved or removed this episode.
          </p>
        </div>
      </div>
    );
  }

  if (!episode) return null;

  const streams = episode.streams || [];
  const downloads = episode.download_links || [];

  // Use anime_title from API (e.g. "Liar Game") + episode number (e.g. 1)
  const epNum = String(episode.episode_number || episode.episode || "");
  const animeTitle = String(episode.anime_title || "");
  const displayTitle =
    animeTitle && epNum
      ? `${animeTitle} Episode ${epNum}`
      : String(episode.title || animeTitle || `Episode ${epNum || slug}`);

  // Empty episode (no streams, no downloads) — likely stale slug
  if (streams.length === 0 && downloads.length === 0) {
    return (
      <div className="space-y-4">
        <Link
          href={`/anime`}
          className="inline-flex items-center gap-1.5 text-sm text-sakura-400 hover:underline"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          Back to Anime
        </Link>
        <h1 className="text-lg font-bold sm:text-xl">{displayTitle}</h1>
        <div className="card text-sm">
          <p className="font-semibold mb-1 text-sakura-200">No stream or download links found</p>
          <p className="text-ink-400">
            The source may have removed or moved this episode. Try opening it
            on the original site.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Link
        href={`/anime/${source}/detail/${slug.split("-")[0]}`}
        className="inline-flex items-center gap-1.5 text-sm text-sakura-400 hover:underline"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
        Back to detail
      </Link>

      <h1 className="text-lg font-bold sm:text-xl">
        {displayTitle}
      </h1>

      {streams.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">Stream Links</h2>
          <div className="grid gap-3">
            {streams.map((s, i) => (
              <VideoPlayer
                key={i}
                url={s.url}
                quality={s.quality}
                host={s.host}
                poster={undefined}
              />
            ))}
          </div>
        </section>
      ) : null}

      {downloads.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">Download Links</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {downloads.map((d, i) => (
              <a
                key={i}
                href={d.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="card card-hover text-sm"
              >
                <span className="font-medium text-ink-100">{d.host || d.quality || `Download ${i + 1}`}</span>
                {d.quality ? <span className="ml-2 text-xs text-ink-400">{d.quality}</span> : null}
              </a>
            ))}
          </div>
        </section>
      ) : null}

      {streams.length === 0 && downloads.length === 0 ? (
        <div className="card text-sm text-ink-400">
          No stream or download links found for this episode.
        </div>
      ) : null}

      {/* Chapter Comments */}
      <ClientComments source={source} slug={slug} kind="anime" />
    </div>
  );
}
