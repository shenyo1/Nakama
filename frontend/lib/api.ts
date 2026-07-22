/**
 * Server-side fetch wrapper against Nakama.
 *
 * - Browser never sees API_KEY (server-only env).
 * - Server components call the internal Docker URL when set
 *   (API_INTERNAL_URL=http://api:8000), otherwise NEXT_PUBLIC_API_BASE.
 * - Client-only helper wsUrl() points at the public API; /ws is not
 *   covered by the anime/comic/novel API-key middleware.
 */
import type { ApiEnvelope, ApiKind, SearchResults, Stats } from "./types";

/** Public browser-facing API origin (for WS / display). */
export const PUBLIC_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

/**
 * Server-side base URL. Prefer the internal compose service so the
 * Next server does not hairpin through Cloudflare.
 */
function serverApiBase(): string {
  const internal = process.env.API_INTERNAL_URL?.replace(/\/$/, "");
  if (internal) return internal;
  return PUBLIC_API_BASE;
}

function serverApiKey(): string {
  // Never NEXT_PUBLIC_ — must stay off the client bundle.
  return process.env.API_KEY || "";
}

/** Client-side WebSocket URL (no secret in the query string). */
export function wsUrl(): string {
  const base = PUBLIC_API_BASE;
  if (base.startsWith("https://")) return base.replace("https://", "wss://") + "/ws";
  if (base.startsWith("http://")) return base.replace("http://", "ws://") + "/ws";
  return "ws://localhost:8000/ws";
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const key = serverApiKey();
  if (key) headers["X-API-Key"] = key;
  return headers;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${serverApiBase()}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init?.headers || {}),
    },
    // Server components: revalidate frequently for data freshness.
    next: { revalidate: 30 },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${path}: ${text.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchStats(): Promise<Stats> {
  const body = await getJson<{ ok: boolean; data: Stats } | Stats>("/stats");
  if (body && typeof body === "object" && "data" in body && body.data) {
    return body.data as Stats;
  }
  return body as Stats;
}

export async function fetchSourceHome(
  kind: ApiKind,
  source: string,
  page = 1
): Promise<unknown[]> {
  const body = await getJson<ApiEnvelope<unknown[] | { items: unknown[] }>>(
    `/${kind}/${source}/home?page=${page}`
  );
  const data = body.data;
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object" && Array.isArray((data as { items?: unknown[] }).items)) {
    return (data as { items: unknown[] }).items;
  }
  return [];
}

export async function fetchSourceSearch(
  kind: ApiKind,
  source: string,
  q: string
): Promise<unknown[]> {
  // Backend routes use path param: /{kind}/{source}/search/{query}
  const body = await getJson<ApiEnvelope<unknown[]>>(
    `/${kind}/${source}/search/${encodeURIComponent(q)}`
  );
  return Array.isArray(body.data) ? body.data : [];
}

export async function crossSearch(
  q: string,
  type: ApiKind = "comic"
): Promise<SearchResults> {
  // Use the new multi-source search endpoints for merged results
  const path = `/${type}/search/${encodeURIComponent(q)}`;
  const body = await getJson<ApiEnvelope<SearchResults> | SearchResults>(path);
  if (body && typeof body === "object" && "data" in body && body.data) {
    return body.data as SearchResults;
  }
  return body as SearchResults;
}

export interface SourceHealthRow {
  name: string;
  kind: string;
  status: "healthy" | "degraded" | "down" | "unknown" | string;
  ok: number;
  fail: number;
  total: number;
  success_rate: number | null;
  last_status: string;
  last_latency_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  last_error: string | null;
  transport?: string;
  notes?: string;
  limitations?: string[];
}

export interface SourceHealthBoard {
  summary: {
    healthy: number;
    degraded: number;
    down: number;
    unknown: number;
    total: number;
  };
  sources: SourceHealthRow[];
  infra?: Record<string, unknown>;
  auto_repair?: {
    enabled: boolean;
    open_breakers?: string[];
    stale_count?: number;
  };
  stale_adapters?: { name: string; age_days: number }[];
}

export async function fetchSourceHealth(
  probe = false
): Promise<SourceHealthBoard> {
  const path = probe ? "/sources/health?probe=true" : "/sources/health";
  const body = await getJson<ApiEnvelope<SourceHealthBoard> | SourceHealthBoard>(
    path,
    // probes can be slow
    { next: { revalidate: 0 } as never }
  );
  if (body && typeof body === "object" && "data" in body && body.data) {
    return body.data as SourceHealthBoard;
  }
  return body as SourceHealthBoard;
}

export const ANIME_SOURCES = ["otakudesu", "kura", "anilist", "jikan", "samehadaku", "anichin"] as const;
export const COMIC_SOURCES = [
  "komiku",
  "kiryuu",
  "komikcast",
  "komikindo",
  "mangadex",
  "shinigami",
  "bacakomik",
  "komikstation",
  "westmanga",
] as const;
export const NOVEL_SOURCES = ["sakuranovel", "novelbin", "novelfull", "meionovels", "novelhubapp"] as const;

// Back-compat alias used by older imports / docs.
export const API_BASE = PUBLIC_API_BASE;
