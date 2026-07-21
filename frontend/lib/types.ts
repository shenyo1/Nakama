/**
 * Shared TypeScript types matching Nakama response shapes.
 *
 * The backend wraps every response in a `{ ok, source, data }` envelope —
 * see `app/schemas.py`. We mirror it here so pages can stay strongly typed
 * without pulling in a generated SDK.
 */

export type ApiKind = "anime" | "comic" | "novel";

export interface ApiEnvelope<T> {
  ok: boolean;
  source?: string;
  data?: T;
  /** Optional top-level error string surfaced by the router. */
  error?: string;
}

export interface Stats {
  sources: Record<ApiKind, string[]>;
  source_counts: Record<ApiKind, number>;
  total_sources: number;
  uptime_seconds: number;
  offline_mode: boolean;
}

export interface SourceInfo {
  source: string;
  kind: ApiKind;
}

export interface AnimeSummary {
  slug: string;
  title: string;
  thumbnail?: string;
  /** Optional metadata surfaced by the upstream scraper. */
  [k: string]: unknown;
}

export interface ComicSummary {
  slug: string;
  title: string;
  thumbnail?: string;
  [k: string]: unknown;
}

export interface NovelSummary {
  slug: string;
  title: string;
  thumbnail?: string;
  [k: string]: unknown;
}

export interface SearchResults {
  query: string;
  type: ApiKind;
  sources_tried: string[];
  sources_failed: { source: string; error: string }[];
  results: Record<string, unknown[]>;
}

export interface WsEvent {
  type?: string;
  source?: string;
  slug?: string;
  chapter?: number | string;
  at?: number | string;
  [k: string]: unknown;
}
