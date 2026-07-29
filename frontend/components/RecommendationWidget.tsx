"use client";

import { useEffect, useState } from "react";
import { ItemCard } from "./ItemCard";
import type { ContentKind, RecommendationResponse } from "../lib/recommendations";

interface Props {
  title: string;
  kind: ContentKind;
  source: string;
  synopsis?: string;
  genres?: string[];
}

export function RecommendationWidget({ title, kind, source, synopsis, genres }: Props) {
  const [recs, setRecs] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchRecs() {
      setLoading(true);
      setError(null);
      try {
        const token = typeof window !== "undefined" ? localStorage.getItem("nakama_token") : null;
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/recommendations`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              title,
              kind,
              limit: 6,
              synopsis: synopsis || undefined,
              genres: genres || undefined,
            }),
          }
        );
        if (!res.ok) {
          throw new Error(`Recommendation API returned ${res.status}`);
        }
        const data: RecommendationResponse = await res.json();
        if (!cancelled) {
          setRecs(data);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    if (title) {
      fetchRecs();
    }

    return () => {
      cancelled = true;
    };
  }, [title, kind, synopsis, genres?.join(",")]);

  if (loading) {
    return (
      <section className="space-y-3">
        <h2 className="text-sm font-semibold sm:text-base">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-3 animate-pulse rounded-full bg-sakura-400/60" />
            You might also like
          </span>
        </h2>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 sm:gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-pulse rounded-lg bg-ink-800">
              <div className="aspect-[3/4] w-full rounded-lg bg-ink-700" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (error || !recs || !recs.recommendations?.length) {
    // Don't show anything if there are no recommendations or an error occurred.
    // This is non-intrusive — the page still works fine without this section.
    return null;
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold sm:text-base">
        <span className="inline-flex items-center gap-1.5">
          <svg className="h-4 w-4 text-sakura-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
          </svg>
          You might also like
        </span>
      </h2>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 sm:gap-3">
        {recs.recommendations.map((rec) => (
          <ItemCard
            key={rec.title}
            title={rec.title}
            subtitle={rec.genres?.slice(0, 2).join(", ")}
            thumbnail={rec.thumbnail}
            source={rec.source || source}
            kind={kind}
            slug={rec.slug || rec.title}
          />
        ))}
      </div>
    </section>
  );
}
