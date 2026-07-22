import { getJson } from "../../../../../lib/api";
import Link from "next/link";

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
        <Link href={`/anime/${source}`} className="text-sm text-sakura-400 hover:underline">← Back</Link>
        <div className="card text-sm text-sakura-200">{error}</div>
      </div>
    );
  }

  if (!episode) return null;

  const streams = episode.streams || [];
  const downloads = episode.download_links || [];

  return (
    <div className="space-y-4">
      <Link
        href={`/anime/${source}/detail/${slug.split("-")[0]}`}
        className="text-sm text-sakura-400 hover:underline"
      >
        ← Back to detail
      </Link>

      <h1 className="text-lg font-bold sm:text-xl">
        {episode.title || `Episode ${episode.episode || slug}`}
      </h1>

      {streams.length > 0 ? (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold">Stream Links</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            {streams.map((s, i) => (
              <a
                key={i}
                href={s.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="card card-hover text-sm"
              >
                <span className="font-medium text-ink-100">{s.host || s.quality || `Stream ${i + 1}`}</span>
                {s.quality ? <span className="ml-2 text-xs text-ink-400">{s.quality}</span> : null}
              </a>
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
    </div>
  );
}
