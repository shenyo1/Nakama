/**
 * Thin fetch wrapper against SankaApi.
 * Base URL from NEXT_PUBLIC_API_BASE (default http://localhost:8000).
 */
import type { ApiEnvelope, ApiKind, SearchResults, Stats } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

export function wsUrl(): string {
  const base = API_BASE;
  if (base.startsWith("https://")) return base.replace("https://", "wss://") + "/ws";
  if (base.startsWith("http://")) return base.replace("http://", "ws://") + "/ws";
  return "ws://localhost:8000/ws";
}

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers || {}),
    },
    // Server components: always revalidate frequently for demo freshness.
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
  const body = await getJson<ApiEnvelope<unknown[]>>(
    `/${kind}/${source}/search?q=${encodeURIComponent(q)}`
  );
  return Array.isArray(body.data) ? body.data : [];
}

export async function crossSearch(
  q: string,
  type: ApiKind = "comic"
): Promise<SearchResults> {
  const body = await getJson<ApiEnvelope<SearchResults> | SearchResults>(
    `/search?q=${encodeURIComponent(q)}&type=${type}`
  );
  if (body && typeof body === "object" && "data" in body && body.data) {
    return body.data as SearchResults;
  }
  return body as SearchResults;
}

export const ANIME_SOURCES = ["otakudesu", "kura", "anilist", "jikan"] as const;
export const COMIC_SOURCES = [
  "komiku",
  "kiryuu",
  "komikcast",
  "mangadex",
  "shinigami",
] as const;
export const NOVEL_SOURCES = ["sakuranovel"] as const;
