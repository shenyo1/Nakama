import { getJson } from "../../../../../lib/api";
import { ClientComments } from "../../../../../components/ClientComments";
import Link from "next/link";
import NakamaReader from "../../../../../components/NakamaReader";

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
  prev_chapter?: string;
  next_chapter?: string;
  [k: string]: unknown;
}

export default async function ComicChapterPage({
  params,
}: {
  params: { source: string; slug: string[] };
}) {
  const { source, slug } = params;
  const fullSlug = Array.isArray(slug) ? slug.join("/") : slug;
  const mangaSlug = fullSlug.split("/")[0];
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
        <Link href="/comic" className="text-sm text-sakura-400 hover:underline">
          ← Back
        </Link>
        <div className="card text-sm text-sakura-200">{error}</div>
      </div>
    );
  }

  if (!chapter) return null;

  return (
    <>
      <NakamaReader chapter={chapter} source={source} mangaSlug={mangaSlug} />
      {/* Chapter Comments */}
      <div className="mt-6">
        <ClientComments source={source} slug={fullSlug} kind="comic" />
      </div>
    </>
  );
}
