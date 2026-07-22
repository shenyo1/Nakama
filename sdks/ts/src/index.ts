// ============================================================================
//  NakamaApi TypeScript SDK — AUTO-GENERATED FILE. DO NOT EDIT.
//
//  Regenerate with: python scripts/gen_ts_sdk.py [--url URL] [--output PATH]
//
//  Source of truth: GET /openapi.json.export on a running NakamaApi instance.
//  Runtime deps    : none — uses the platform fetch API directly.
// ============================================================================

export interface NakamaApiOptions {
  /** Base URL of the NakamaApi deployment. No trailing slash. */
  baseUrl: string;
  /** Default headers sent with every request (e.g. { "X-API-Key": "..." }). */
  headers?: Record<string, string>;
  /** Optional fetch override — useful for Node 18 < environments. */
  fetch?: typeof fetch;
}

/** Internal handle shared across groups — never instantiated by callers. */
export interface NakamaApiClient {
  baseUrl: string;
  headers: Record<string, string>;
  _fetch: typeof fetch;
}

/**
 * Thrown by every endpoint when the response status is not 2xx.
 *
 * The original body is kept on ``.body`` (string) so callers can do their
 * own structured parsing. ``status`` is the numeric HTTP status code.
 */
export class NakamaApiError extends Error {
  readonly status: number;
  readonly body: string;
  constructor(status: number, body: string) {
    super(`NakamaApi request failed: ${status} ${body}`);
    this.status = status;
    this.body = body;
    this.name = "NakamaApiError";
  }
}

/**
 * Generic request options accepted by every generated endpoint method.
 * Groups accept their own typed subset of ``params`` for typed query/body
 * input but this base is exposed for advanced use cases.
 */
export interface NakamaApiRequestInit {
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}

// -- Component schemas (TypeScript interfaces) --------------------

export interface AnimeDetail { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "status"?: string; "score"?: string; "released"?: string; "japanese_title"?: string; "synopsis"?: string; "genres"?: Array<string>; "episodes_count"?: string; "studios"?: string; "episodes"?: Array<Record<string, unknown>> }
export interface ApiResponse { "ok"?: boolean; "source"?: string; "data": unknown }
export interface ApiResponse_AnimeDetail { "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "status"?: string; "score"?: string; "released"?: string; "japanese_title"?: string; "synopsis"?: string; "genres"?: Array<string>; "episodes_count"?: string; "studios"?: string; "episodes"?: Array<Record<string, unknown>> } }
export interface ApiResponse_ComicDetail { "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "views"?: string; "latest_chapter"?: string; "author"?: string; "status"?: string; "genres"?: Array<string>; "synopsis"?: string; "chapters"?: Array<Record<string, unknown>> } }
export interface ApiResponse_NovelDetail { "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "status"?: string; "rating"?: string; "latest_chapter"?: string; "author"?: string; "synopsis"?: string; "genres"?: Array<string>; "chapters"?: Array<Record<string, unknown>> } }
export interface BookmarkCreate { "source": string; "content_id": string; "content_type": "anime" | "comic" | "novel"; "title"?: string; "thumbnail"?: string; "note"?: string }
export interface BroadcastBody { "event": Record<string, unknown> }
export interface ComicDetail { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "views"?: string; "latest_chapter"?: string; "author"?: string; "status"?: string; "genres"?: Array<string>; "synopsis"?: string; "chapters"?: Array<Record<string, unknown>> }
export interface HTTPValidationError { "detail"?: Array<{ "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown> }> }
export interface HistoryCreate { "source": string; "content_id": string; "content_type": "anime" | "comic" | "novel"; "chapter_id": string; "user_id"?: number }
export interface HistoryEntry { "id": number; "user_id": number; "source": string; "content_id": string; "content_type": string; "chapter_id": string; "read_at": string }
export interface LoginBody { "username": string; "password": string }
export interface NovelDetail { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "status"?: string; "rating"?: string; "latest_chapter"?: string; "author"?: string; "synopsis"?: string; "genres"?: Array<string>; "chapters"?: Array<Record<string, unknown>> }
export interface PreferencesIn { "payload"?: Record<string, unknown> }
export interface PreferencesOut { "payload": Record<string, unknown>; "updated_at"?: string }
export interface RefreshBody { "refresh_token": string }
export interface RegisterBody { "username": string; "password": string }
export interface ValidationError { "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown> }
export interface WebhookCreate { "url": string; "source"?: string; "content_type"?: "anime" | "comic" | "novel"; "secret"?: string }

// -- Endpoint groups --------------------------------------------------

export class Anime {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Anime documentation / source list
   * @see GET /anime/
   */
  async anime(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/anime/${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Search across all anime sources (deduplicated, scored)
   * @see GET /anime/search/{query}
   * Search every anime source concurrently, deduplicate by normalized title.
   * 
   * Returns a unified list with each item annotated by ``_sources`` showing
   * which sources returned this title. Useful for finding the most widely
   * available show.
   */
  async search(query: string, params?: { "page"?: number; "page_size"?: number }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/anime/search/${query}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Anime detail
   * @see GET /anime/{source}/detail/{slug}
   */
  async detail(source: string, slug: string): Promise<{ "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "status"?: string; "score"?: string; "released"?: string; "japanese_title"?: string; "synopsis"?: string; "genres"?: Array<string>; "episodes_count"?: string; "studios"?: string; "episodes"?: Array<Record<string, unknown>> } }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/anime/${source}/detail/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "status"?: string; "score"?: string; "released"?: string; "japanese_title"?: string; "synopsis"?: string; "genres"?: Array<string>; "episodes_count"?: string; "studios"?: string; "episodes"?: Array<Record<string, unknown>> } };
  }

  /**
   * Stream/download links for an episode
   * @see GET /anime/{source}/episode/{slug}
   */
  async episode(source: string, slug: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/anime/${source}/episode/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Anime in a genre
   * @see GET /anime/{source}/genre/{slug}
   */
  async genre(source: string, slug: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/anime/${source}/genre/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * All genres
   * @see GET /anime/{source}/genres
   */
  async genres(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/anime/${source}/genres${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Latest ongoing anime
   * @see GET /anime/{source}/home
   */
  async home(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/anime/${source}/home${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Search anime
   * @see GET /anime/{source}/search/{query}
   */
  async search_get(source: string, query: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/anime/${source}/search/${query}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

}
export class Comic {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Comic documentation / source list
   * @see GET /comic/
   */
  async comic(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/comic/${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Chapter image list
   * @see GET /comic/{source}/chapter/{slug}
   */
  async chapter(source: string, slug: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/comic/${source}/chapter/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Comics in a genre
   * @see GET /comic/{source}/genre/{slug}
   */
  async genre(source: string, slug: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/${source}/genre/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Latest comics
   * @see GET /comic/{source}/home
   */
  async home(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/${source}/home${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Recently updated comics
   * @see GET /comic/{source}/latest
   */
  async latest(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/${source}/latest${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Comic detail + chapter list
   * @see GET /comic/{source}/manga/{slug}
   */
  async manga(source: string, slug: string): Promise<{ "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "views"?: string; "latest_chapter"?: string; "author"?: string; "status"?: string; "genres"?: Array<string>; "synopsis"?: string; "chapters"?: Array<Record<string, unknown>> } }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/comic/${source}/manga/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "views"?: string; "latest_chapter"?: string; "author"?: string; "status"?: string; "genres"?: Array<string>; "synopsis"?: string; "chapters"?: Array<Record<string, unknown>> } };
  }

  /**
   * Popular comics
   * @see GET /comic/{source}/popular
   */
  async popular(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/${source}/popular${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Search comics
   * @see GET /comic/{source}/search/{query}
   */
  async search(source: string, query: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/${source}/search/${query}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

}
export class Novel {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Novel documentation / source list
   * @see GET /novel/
   */
  async novel(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/novel/${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Search across all novel sources (deduplicated, scored)
   * @see GET /novel/search/{query}
   * Search every novel source concurrently, deduplicate by normalized title.
   * 
   * Each merged item carries ``_sources`` showing which sources returned it.
   * Sources that fail are listed in ``sources_failed``; the rest still
   * contribute to the merged result.
   */
  async search(query: string, params?: { "page"?: number; "page_size"?: number }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/novel/search/${query}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Chapter text (novel prose)
   * @see GET /novel/{source}/chapter/{slug}
   */
  async chapter(source: string, slug: string): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/novel/${source}/chapter/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Novel detail + chapter list
   * @see GET /novel/{source}/detail/{slug}
   */
  async detail(source: string, slug: string): Promise<{ "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "status"?: string; "rating"?: string; "latest_chapter"?: string; "author"?: string; "synopsis"?: string; "genres"?: Array<string>; "chapters"?: Array<Record<string, unknown>> } }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/novel/${source}/detail/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "status"?: string; "rating"?: string; "latest_chapter"?: string; "author"?: string; "synopsis"?: string; "genres"?: Array<string>; "chapters"?: Array<Record<string, unknown>> } };
  }

  /**
   * Novels in a genre (paginated upstream)
   * @see GET /novel/{source}/genre/{slug}
   * Novels in a genre.
   * 
   * ``page`` is the *upstream* genre page (passed to ``genre``); ``page_size``
   * paginates the returned slice locally.
   */
  async genre(source: string, slug: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/novel/${source}/genre/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * All genres
   * @see GET /novel/{source}/genres
   */
  async genres(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/novel/${source}/genres${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Latest novels (paginated upstream)
   * @see GET /novel/{source}/home
   * Latest novels.
   * 
   * ``page`` here is the *upstream* page (passed to the source's ``home``);
   * ``page_size`` paginates the returned slice locally.
   */
  async home(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/novel/${source}/home${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Popular novels
   * @see GET /novel/{source}/popular
   */
  async popular(source: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/novel/${source}/popular${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Search novels
   * @see GET /novel/{source}/search/{query}
   */
  async search_get(source: string, query: string, params?: { "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/novel/${source}/search/${query}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

}
export class Search {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Cross-source search (anime/comic/novel)
   * @see GET /search
   * Search every source of *type* for *q* and return per-source results.
   */
  async cross(params?: { "q": string; "type"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.q !== undefined) search.set("q", String(p.q));
    if (p.type !== undefined) search.set("type", String(p.type));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/search${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

}
export class Image {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Proxy a remote image with SSRF protection
   * @see GET /image
   * Fetch *url* server-side and stream the raw bytes back.
   * 
   * This endpoint exists so a browser frontend can render chapter page images
   * that would otherwise be blocked by hotlink protection or CORS. The server
   * validates that *url* is a public http(s) resource before fetching — any
   * scheme other than http/https, and any host that resolves into a private
   * IP range, is rejected with HTTP 400.
   */
  async image(params?: { "url": string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.url !== undefined) search.set("url", String(p.url));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/image${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

}
export class History {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * List reading history for a user
   * @see GET /history
   */
  async get(params?: { "user_id"?: number; "content_type"?: "anime" | "comic" | "novel"; "limit"?: number }): Promise<Array<{ "id": number; "user_id": number; "source": string; "content_id": string; "content_type": string; "chapter_id": string; "read_at": string }>> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.user_id !== undefined) search.set("user_id", String(p.user_id));
    if (p.content_type !== undefined) search.set("content_type", String(p.content_type));
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/history${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as Array<{ "id": number; "user_id": number; "source": string; "content_id": string; "content_type": string; "chapter_id": string; "read_at": string }>;
  }

  /**
   * Record a reading event
   * @see POST /history
   */
  async post(params?: { body: { "source": string; "content_id": string; "content_type": "anime" | "comic" | "novel"; "chapter_id": string; "user_id"?: number } }): Promise<{ "id": number; "user_id": number; "source": string; "content_id": string; "content_type": string; "chapter_id": string; "read_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/history${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "id": number; "user_id": number; "source": string; "content_id": string; "content_type": string; "chapter_id": string; "read_at": string };
  }

}
export class Ws {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Manually broadcast a JSON event to every connected /ws client
   * @see POST /admin/broadcast
   * Forward ``payload.event`` to every connected WebSocket.
   * 
   * When ``API_KEY`` is configured, the caller must send the matching
   * ``X-API-Key`` header. The HTTP-level auth middleware in ``main.py``
   * already exempts non-/anime/comic/novel paths, so the admin endpoint
   * is unrestricted by that middleware; we enforce the API key here
   * explicitly so the gate still works.
   */
  async admin(params?: { body: { "event": Record<string, unknown> } }): Promise<Record<string, unknown>> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/admin/broadcast${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as Record<string, unknown>;
  }

}
export class Stats {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Cache + cost guard analytics
   * @see GET /analytics
   * Lightweight ops analytics for Tier 3.
   * 
   * * request rate (last 60s / 5m) from this process
   * * CF cache status histogram from recent samples (if any)
   * * process uptime / worker count / memory if available
   */
  async analytics(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/analytics${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Recent audit log entries
   * @see GET /audit
   */
  async audit(params?: { "limit"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/audit${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Login and get JWT pair
   * @see POST /auth/login
   */
  async login(params?: { body: { "username": string; "password": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/login${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Current user from Bearer token
   * @see GET /auth/me
   */
  async me(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/me${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Quota remaining for current principal
   * @see GET /auth/quota
   */
  async quota(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/quota${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Refresh access token
   * @see POST /auth/refresh
   */
  async refresh(params?: { body: { "refresh_token": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/refresh${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Register a user
   * @see POST /auth/register
   */
  async register(params?: { body: { "username": string; "password": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/register${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * List Bookmarks
   * @see GET /bookmarks
   */
  async list(params?: { "content_type"?: "anime" | "comic" | "novel"; "limit"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.content_type !== undefined) search.set("content_type", String(p.content_type));
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/bookmarks${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Create Bookmark
   * @see POST /bookmarks
   */
  async create(params?: { body: { "source": string; "content_id": string; "content_type": "anime" | "comic" | "novel"; "title"?: string; "thumbnail"?: string; "note"?: string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/bookmarks${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Delete Bookmark
   * @see DELETE /bookmarks/{bookmark_id}
   */
  async delete(bookmark_id: string): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/bookmarks/${bookmark_id}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "DELETE",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Chapter images across comic sources with fallback
   * @see GET /comic/chapter/{slug}
   * First source returning a non-empty ``images`` list wins.
   * 
   * Komikcast (which needs a JWT) is intentionally last so other free sources
   * can serve images first.
   */
  async fallback_get_x(slug: string, params?: { "primary"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.primary !== undefined) search.set("primary", String(p.primary));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/chapter/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Find manga detail across comic sources with fallback
   * @see GET /comic/manga/{slug}
   */
  async fallback_get(slug: string, params?: { "primary"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.primary !== undefined) search.set("primary", String(p.primary));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/manga/${slug}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Search across comic sources with fallback
   * @see GET /comic/search/{query}
   */
  async fallback(query: string, params?: { "primary"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.primary !== undefined) search.set("primary", String(p.primary));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic/search/${query}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as unknown;
  }

  /**
   * Health
   * @see GET /health
   * Liveness probe.
   * 
   * Returns the active source list and the current OFFLINE_MODE setting.
   * Performs no network I/O — safe to call in air-gapped / CI environments.
   */
  async health(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/health${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Recent outage / recovery events
   * @see GET /outages
   * Return the tail of the outages JSONL log (newest last, then reversed).
   */
  async outages(params?: { "limit"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/outages${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Recommendations
   * @see GET /recommend/{content_type}
   * Recommend titles.
   * 
   * - anime: AniList recommendations (or popular if no seed)
   * - comic: MangaDex popular / related-ish via search seed
   * - novel: sakuranovel popular fallback
   */
  async recommend(content_type: string, params?: { "seed"?: string; "limit"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.seed !== undefined) search.set("seed", String(p.seed));
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/recommend/${content_type}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Source health scoreboard
   * @see GET /sources/health
   * Return per-source health from Redis/memory counters.
   * 
   * Without ``probe=true`` this is pure counter reads (fast). With
   * ``probe=true`` the API hits each source home once and updates the board.
   */
  async sources(params?: { "probe"?: boolean }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.probe !== undefined) search.set("probe", String(p.probe));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/sources/health${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Probe a single source
   * @see GET /sources/health/{name}
   */
  async source(name: string, params?: { "probe"?: boolean }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.probe !== undefined) search.set("probe", String(p.probe));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/sources/health/${name}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Stats
   * @see GET /stats
   * Operational stats: source counts, total, uptime, and mode flag.
   * 
   * Pure-process introspection — no network calls — so this endpoint is safe
   * to hit in offline mode and from liveness/readiness probes.
   */
  async stats(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/stats${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Trending titles
   * @see GET /trending/{content_type}
   */
  async trending(content_type: string, params?: { "limit"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/trending/${content_type}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * List Webhooks
   * @see GET /webhooks
   */
  async list_get(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/webhooks${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Create Webhook
   * @see POST /webhooks
   */
  async create_post(params?: { body: { "url": string; "source"?: string; "content_type"?: "anime" | "comic" | "novel"; "secret"?: string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/webhooks${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Test Webhook
   * @see POST /webhooks/test/{webhook_id}
   * Fire a sample event to the registered URL (HMAC signed if secret set).
   */
  async test(webhook_id: string): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/webhooks/test/${webhook_id}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "POST",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

  /**
   * Delete Webhook
   * @see DELETE /webhooks/{webhook_id}
   */
  async delete_delete(webhook_id: string): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/webhooks/${webhook_id}${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "DELETE",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "ok"?: boolean; "source"?: string; "data": unknown };
  }

}
export class Preferences {
  private readonly _client: NakamaApiClient;
  constructor(client: NakamaApiClient) {
    this._client = client;
  }

  /**
   * Reset preferences to defaults
   * @see DELETE /preferences
   */
  async delete(): Promise<{ "payload": Record<string, unknown>; "updated_at"?: string }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/preferences${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "DELETE",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "payload": Record<string, unknown>; "updated_at"?: string };
  }

  /**
   * Get current user preferences
   * @see GET /preferences
   */
  async get(): Promise<{ "payload": Record<string, unknown>; "updated_at"?: string }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/preferences${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json" };
    const init: RequestInit = {
      method: "GET",
      headers: hdrs,
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "payload": Record<string, unknown>; "updated_at"?: string };
  }

  /**
   * Merge partial update into preferences
   * @see PATCH /preferences
   */
  async patch(params?: { body: { "payload"?: Record<string, unknown> } }): Promise<{ "payload": Record<string, unknown>; "updated_at"?: string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/preferences${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "PATCH",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "payload": Record<string, unknown>; "updated_at"?: string };
  }

  /**
   * Replace current user preferences
   * @see PUT /preferences
   */
  async put(params?: { body: { "payload"?: Record<string, unknown> } }): Promise<{ "payload": Record<string, unknown>; "updated_at"?: string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/preferences${suffix}`;
    const hdrs: Record<string, string> = { ...this._client.headers, "Accept": "application/json", "Content-Type": "application/json" };
    const init: RequestInit = {
      method: "PUT",
      headers: hdrs,
      body: JSON.stringify(p.body),
    };
    const res = await this._client._fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new NakamaApiError(res.status, text || res.statusText);
    }
    return (await res.json()) as { "payload": Record<string, unknown>; "updated_at"?: string };
  }

}

// -- Top-level client -------------------------------------------------

export class NakamaApi {
  readonly anime: Anime;
  readonly comic: Comic;
  readonly novel: Novel;
  readonly search: Search;
  readonly image: Image;
  readonly history: History;
  readonly ws: Ws;
  readonly stats: Stats;
  readonly preferences: Preferences;

  constructor(opts: NakamaApiOptions) {
    const client: NakamaApiClient = {
      baseUrl: opts.baseUrl.replace(/\/$/, ""),
      headers: opts.headers ?? {},
      _fetch: opts.fetch ?? ((...args: Parameters<typeof fetch>) => fetch(...args)),
    };
    this.anime = new Anime(client);
    this.comic = new Comic(client);
    this.novel = new Novel(client);
    this.search = new Search(client);
    this.image = new Image(client);
    this.history = new History(client);
    this.ws = new Ws(client);
    this.stats = new Stats(client);
    this.preferences = new Preferences(client);
  }
}
// -- Default export --------------------------------------------------
export default NakamaApi;
