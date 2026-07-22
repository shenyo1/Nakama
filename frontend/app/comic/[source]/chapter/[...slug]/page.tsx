import { getJson } from "../../../../../lib/api";
import Link from "next/link";

export const runtime = "edge";
export const dynamic = "force-dynamic";

interface ChapterImage {
  url?: string;
  src?: string;
  [k: string]: unknown;
}

interface ChapterDetail {
  title?: string;
  slug?: string;
  images?: ChapterImage[];
  chapter?: number | string;
  [k: string]: unknown;
}

export default async function ComicChapterPage({
  params,
}: {
  params: { source: string; slug: string[] };
}) {
  const { source, slug } = params;
  const fullSlug = Array.isArray(slug) ? slug.join("/") : slug;
  let chapter: ChapterDetail | null = null;
  let error: string | null = null;

  try {
    const body = await getJson<{ data: ChapterDetail }>(`/comic/${source}/chapter/${fullSlug}`);
    chapter = body.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href={`/comic/${source}`} className="text-sm text-sakura-400 hover:underline">
          ← Back
        </Link>
        <div className="card text-sm text-sakura-200">{error}</div>
      </div>
    );
  }

  if (!chapter) return null;

  const images = chapter.images || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link
          href={`/comic/${source}/manga/${fullSlug.split("/")[0]}`}
          className="text-sm text-sakura-400 hover:underline"
        >
          ← Back to detail
        </Link>
        <h1 className="text-lg font-bold sm:text-xl truncate ml-4">
          {chapter.title || `Chapter ${chapter.chapter || fullSlug}`}
        </h1>
      </div>

      {images.length > 0 ? (
        <div className="space-y-1">
          {images.map((img, i) => {
            const src = img.url || img.src || (typeof img === "string" ? img : "");
            if (!src) return null;
            return (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={i}
                src={`/api/backend/image?url=${encodeURIComponent(src)}`}
                alt={`Page ${i + 1}`}
                className="mx-auto w-full max-w-2xl rounded"
                loading={i < 3 ? "eager" : "lazy"}
              />
            );
          })}
        </div>
      ) : (
        <div className="card text-sm text-ink-400">
          No images found for this chapter. The source may require authentication or JS rendering.
        </div>
      )}

      <div className="flex justify-between pt-4">
        <Link
          href={`/comic/${source}/manga/${fullSlug.split("/")[0]}`}
          className="btn-ghost text-xs"
        >
          ← Chapter list
        </Link>
      </div>
    </div>
  );
}
