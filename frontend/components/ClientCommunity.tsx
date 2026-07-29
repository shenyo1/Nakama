"use client";

import { ReviewForm } from "./ReviewForm";
import { ReviewList } from "./ReviewList";
import { CommentSection } from "./CommentSection";

interface ClientCommunityProps {
  source: string;
  slug: string;
  kind: "anime" | "comic" | "novel";
}

/**
 * Client-side wrapper that bundles ReviewForm, ReviewList, and CommentSection
 * so server components (which can't import "use client" components directly in
 * the same file) can render the community section with a single import.
 */
export function ClientCommunity({ source, slug, kind }: ClientCommunityProps) {
  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-base font-semibold sm:text-lg mb-4">Reviews</h2>
        <ReviewForm source={source} slug={slug} kind={kind} />
        <div className="mt-4">
          <ReviewList source={source} slug={slug} kind={kind} />
        </div>
      </section>

      <section>
        <h2 className="text-base font-semibold sm:text-lg mb-4">Comments</h2>
        <CommentSection source={source} slug={slug} kind={kind} />
      </section>
    </div>
  );
}
