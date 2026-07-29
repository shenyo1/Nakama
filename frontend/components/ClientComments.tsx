"use client";

import { CommentSection } from "./CommentSection";

interface ClientCommentsProps {
  source: string;
  slug: string;
  kind: "anime" | "comic" | "novel";
}

/**
 * Client-side wrapper for CommentSection so server components can render
 * chapter-level comments with a single import.
 */
export function ClientComments({ source, slug, kind }: ClientCommentsProps) {
  return (
    <section className="space-y-4">
      <h2 className="text-base font-semibold sm:text-lg">Chapter Comments</h2>
      <CommentSection source={source} slug={slug} kind={kind} />
    </section>
  );
}
