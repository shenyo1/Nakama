import { getJson } from "../../../../../lib/api";
import { ClientComments } from "../../../../../components/ClientComments";
import Link from "next/link";
import { BackLink } from "../../../../../components/BackLink";

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
        <BackLink href="/novel" label="Back" />
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
        className="inline-flex items-center gap-1.5 text-sm text-sakura-400 hover:underline"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <line x1="19" y1="12" x2="5" y2="12" />
          <polyline points="12 19 5 12 12 5" />
        </svg>
        Back to detail
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

      {/* Chapter Comments */}
      <ClientComments source={source} slug={slug} kind="novel" />
    </div>
  );
}
