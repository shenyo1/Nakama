import { getJson } from "../../../../../lib/api";
import Link from "next/link";

export const runtime = "edge";
export const dynamic = "force-dynamic";

interface NovelChapter {
  title?: string;
  slug?: string;
  chapter?: number | string;
  text?: string;
  paragraphs?: string[];
  content?: string;
  [k: string]: unknown;
}

export default async function NovelChapterPage({
  params,
}: {
  params: { source: string; slug: string };
}) {
  const { source, slug } = params;
  let chapter: NovelChapter | null = null;
  let error: string | null = null;

  try {
    const body = await getJson<{ data: NovelChapter }>(`/novel/${source}/chapter/${slug}`);
    chapter = body.data;
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <Link href={`/novel/${source}`} className="text-sm text-sakura-400 hover:underline">← Back</Link>
        <div className="card text-sm text-sakura-200">{error}</div>
      </div>
    );
  }

  if (!chapter) return null;

  // Novel chapters return text content — could be paragraphs[], text string, or content
  const paragraphs: string[] = chapter.paragraphs || [];
  const textContent = chapter.text || chapter.content || "";
  const allParagraphs = paragraphs.length > 0
    ? paragraphs
    : textContent
      ? textContent.split("\n").filter((p) => p.trim().length > 0)
      : [];

  return (
    <div className="space-y-4">
      <Link
        href={`/novel/${source}/detail/${slug.split("-").slice(0, -1).join("-") || slug}`}
        className="text-sm text-sakura-400 hover:underline"
      >
        ← Back to detail
      </Link>

      <h1 className="text-lg font-bold sm:text-xl">
        {chapter.title || `Chapter ${chapter.chapter || slug}`}
      </h1>

      {allParagraphs.length > 0 ? (
        <article className="card prose prose-invert max-w-none">
          <div className="space-y-3">
            {allParagraphs.map((p, i) => (
              <p key={i} className="text-sm text-ink-200 leading-relaxed">{p}</p>
            ))}
          </div>
        </article>
      ) : (
        <div className="card text-sm text-ink-400">
          No text content found for this chapter.
        </div>
      )}
    </div>
  );
}
