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
export interface Body_upload_avatar_creator_profile_avatar_post { "file": string }
export interface Body_upload_cover_creator_upload_cover_post { "file": string }
export interface BookmarkCreate { "source": string; "content_id": string; "content_type": "anime" | "comic" | "novel"; "title"?: string; "thumbnail"?: string; "note"?: string }
export interface BroadcastBody { "event": Record<string, unknown> }
export interface ChangePasswordBody { "current_password": string; "new_password": string }
export interface ChapterCreate { "series_id": number; "title": string; "chapter_number": number; "content": string; "content_format"?: string; "published"?: boolean }
export interface ChapterOut { "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }
export interface ChapterUpdate { "title"?: string; "chapter_number"?: number; "content"?: string; "content_format"?: string; "published"?: boolean }
export interface ClientError { "message": string; "stack"?: string; "source"?: string; "severity"?: string; "extra"?: Record<string, unknown> }
export interface ComicDetail { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "views"?: string; "latest_chapter"?: string; "author"?: string; "status"?: string; "genres"?: Array<string>; "synopsis"?: string; "chapters"?: Array<Record<string, unknown>> }
export interface ComicGenerateRequest { "prompt": string; "style"?: string; "panels"?: number }
export interface CommentCreate { "kind": "anime" | "comic" | "novel"; "body": string; "parent_id"?: number }
export interface CommentOut { "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "body": string; "parent_id"?: number; "created_at": string; "replies"?: Array<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "body": string; "parent_id"?: number; "created_at": string; "replies"?: Array<unknown> }> }
export interface ConfirmBody { "token": string }
export interface CreatorApplicationIn { "pen_name": string; "bio"?: string; "portfolio_url"?: string; "sample_work"?: string; "content_types": string }
export interface CreatorBrowseItem { "id": number; "display_name": string; "avatar_url"?: string; "bio"?: string; "follower_count"?: number; "series_count"?: number; "verified"?: boolean }
export interface DashboardOut { "profile": { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }; "series_count": number; "total_chapters": number; "total_views": number; "total_followers": number; "revenue_estimate": number; "recent_series": Array<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }>; "top_chapters": Array<{ "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> }
export interface FeedItem { "type": "review" | "comment" | "list"; "user_id": number; "username"?: string; "data": Record<string, unknown>; "created_at": string }
export interface FollowStatus { "following": boolean; "follower_count": number }
export interface ForgotBody { "email": string; "base_url"?: string }
export interface HTTPValidationError { "detail"?: Array<{ "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown> }> }
export interface HistoryCreate { "source": string; "content_id": string; "content_type": "anime" | "comic" | "novel"; "chapter_id": string; "user_id"?: number }
export interface HistoryEntry { "id": number; "user_id": number; "source": string; "content_id": string; "content_type": string; "chapter_id": string; "read_at": string }
export interface LoginBody { "username": string; "password": string }
export interface NovelDetail { "title": string; "slug"?: string; "url"?: string; "thumbnail"?: string; "type"?: string; "status"?: string; "rating"?: string; "latest_chapter"?: string; "author"?: string; "synopsis"?: string; "genres"?: Array<string>; "chapters"?: Array<Record<string, unknown>> }
export interface PreferencesIn { "payload"?: Record<string, unknown> }
export interface PreferencesOut { "payload": Record<string, unknown>; "updated_at"?: string }
export interface ProfileOut { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }
export interface ProfileUpdate { "display_name"?: string; "bio"?: string; "social_links"?: Record<string, unknown> }
export interface ReadingListCreate { "name": string; "is_public"?: boolean }
export interface ReadingListItemCreate { "source": string; "slug": string; "kind": "anime" | "comic" | "novel" }
export interface ReadingListItemOut { "id": number; "source": string; "slug": string; "kind": string; "added_at": string }
export interface ReadingListOut { "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> }
export interface ReadingListUpdate { "name"?: string; "is_public"?: boolean }
export interface RecommendationItem { "title": string; "slug"?: string; "source"?: string; "score": number; "thumbnail"?: string; "genres"?: Array<string> }
export interface RecommendationRequest { "title": string; "kind": "anime" | "comic" | "novel"; "limit"?: number; "synopsis"?: string; "genres"?: Array<string> }
export interface RecommendationResponse { "ok"?: boolean; "anchor": string; "kind": string; "recommendations": Array<{ "title": string; "slug"?: string; "source"?: string; "score": number; "thumbnail"?: string; "genres"?: Array<string> }>; "cached"?: boolean }
export interface RefreshBody { "refresh_token": string }
export interface ResetBody { "token": string; "new_password": string }
export interface ReviewAggregate { "count": number; "avg_rating": number; "distribution": Record<string, unknown> }
export interface ReviewCreate { "kind": "anime" | "comic" | "novel"; "rating": number; "body": string }
export interface ReviewOut { "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "rating": number; "body": string; "created_at": string }
export interface SeriesCreate { "title": string; "description"?: string; "kind": string; "cover_image"?: string }
export interface SeriesOut { "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }
export interface SeriesUpdate { "title"?: string; "description"?: string; "kind"?: string; "cover_image"?: string; "status"?: string; "published"?: boolean }
export interface ValidationError { "loc": Array<string | number>; "msg": string; "type": string; "input"?: unknown; "ctx"?: Record<string, unknown> }
export interface WebhookCreate { "url": string; "source"?: string; "content_type"?: "anime" | "comic" | "novel"; "secret"?: string }
export interface app__routers__auth__RegisterBody { "username": string; "password": string; "email"?: string }
export interface app__routers__creator__RegisterBody { "display_name": string; "bio"?: string; "social_links"?: Record<string, unknown> }

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
  async home(source: string, params?: { "cursor"?: string; "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.cursor !== undefined) search.set("cursor", String(p.cursor));
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
  async home(source: string, params?: { "cursor"?: string; "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.cursor !== undefined) search.set("cursor", String(p.cursor));
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
   * 
   * Results are cached for 30s (configurable via RESPONSE_CACHE_TTL_SECONDS)
   * to avoid re-fanning-out on repeated queries within a session.
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
   * List recent errors (admin)
   * @see GET /admin/errors
   * Return the most recent client/server errors. Requires X-API-Key.
   */
  async list_get_x_x_x(params?: { "limit"?: number; "severity"?: string }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    if (p.severity !== undefined) search.set("severity", String(p.severity));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/admin/errors${suffix}`;
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
   * List Gallery
   * @see GET /ai/gallery
   * Browse community-generated AI comics.
   */
  async list_get_x_x(params?: { "style"?: string; "limit"?: number; "offset"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.style !== undefined) search.set("style", String(p.style));
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    if (p.offset !== undefined) search.set("offset", String(p.offset));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/ai/gallery${suffix}`;
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
   * Get Comic
   * @see GET /ai/gallery/{public_id}
   * Get a single generated comic by its public ID.
   */
  async get_get_x_x_x_x(public_id: string): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/ai/gallery/${public_id}${suffix}`;
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
   * Generate Comic
   * @see POST /ai/generate
   * Generate an AI comic from a text prompt.
   * 
   * Accepts a story prompt, style selection, and panel count (1-6).
   * Returns panel descriptions and generated image URLs.
   */
  async generate(params?: { body: { "prompt": string; "style"?: string; "panels"?: number } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/ai/generate${suffix}`;
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
   * List Styles
   * @see GET /ai/styles
   * List the art styles accepted by ``POST /ai/generate``.
   * 
   * Single source of truth: the same ``STYLE_MODIFIERS`` dict that drives
   * panel generation. Frontends use this to render a style picker without
   * hardcoding the catalog, so adding a style here automatically extends
   * both the picker and the validator.
   * 
   * Public (no auth) — matches ``/ai/gallery`` and lives under the ``/ai``
   * prefix that ``_PUBLIC_PREFIXES`` whitelists in ``app/main.py``.
   */
  async list_get_x(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/ai/styles${suffix}`;
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
   * Cache + cost guard analytics
   * @see GET /analytics
   * Lightweight ops analytics for Tier 3.
   * 
   * * request rate (last 60s / 5m) from this process
   * * CF cache status histogram from recent samples (if any)
   * * process uptime / worker count / memory if available
   * * search latency stats (p50, p95, p99)
   * * per-source latency stats
   * * cache backend stats
   * * quota tier overview
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
   * Search performance breakdown
   * @see GET /analytics/search
   * Detailed search performance analytics.
   * 
   * Shows latency distribution by kind (anime/comic/novel),
   * slowest queries, and cache hit ratio for search endpoints.
   */
  async search(): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/analytics/search${suffix}`;
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
   * Change password (authenticated user)
   * @see POST /auth/change-password
   * Change the password for the currently authenticated user.
   * Requires the current password to be provided for verification.
   */
  async change(params?: { body: { "current_password": string; "new_password": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/change-password${suffix}`;
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
   * Confirm an email address via token (email link)
   * @see GET /auth/confirm
   * Accept token via query string (GET — email link).
   */
  async auth(params?: { "token"?: string }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.token !== undefined) search.set("token", String(p.token));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/auth/confirm${suffix}`;
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
   * Confirm an email address via token (JSON body)
   * @see POST /auth/confirm
   * Accept token via JSON body (POST — API).
   */
  async auth_post(params?: { body: { "token": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/confirm${suffix}`;
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
   * Request a password-reset link
   * @see POST /auth/forgot
   * Always returns 200 to avoid user-enumeration. The reset link is sent
   * via SMTP when configured, or returned in the response payload when
   * SMTP is disabled (so local installs still work).
   * 
   * Uses ``scalars().first()`` instead of ``scalar_one_or_none()`` to be
   * resilient to duplicate email rows (defensive — the DB has a partial
   * UNIQUE index on non-empty emails, but legacy data or races could
   * still produce dupes). If multiple rows match, picks the first.
   */
  async forgot(params?: { body: { "email": string; "base_url"?: string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/forgot${suffix}`;
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
  async register(params?: { body: { "username": string; "password": string; "email"?: string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
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
   * Complete a password reset
   * @see POST /auth/reset
   */
  async reset(params?: { body: { "token": string; "new_password": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/auth/reset${suffix}`;
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
   * @see GET /comic-fallback/chapter/{slug}
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
    const url = `${this._client.baseUrl}/comic-fallback/chapter/${slug}${suffix}`;
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
   * @see GET /comic-fallback/manga/{slug}
   */
  async fallback_get(slug: string, params?: { "primary"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.primary !== undefined) search.set("primary", String(p.primary));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic-fallback/manga/${slug}${suffix}`;
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
   * @see GET /comic-fallback/search/{query}
   */
  async fallback(query: string, params?: { "primary"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.primary !== undefined) search.set("primary", String(p.primary));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comic-fallback/search/${query}${suffix}`;
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
   * Get threaded comments for content
   * @see GET /comments/{source}/{slug}
   */
  async get_get_x(source: string, slug: string, params?: { "kind"?: "anime" | "comic" | "novel"; "page"?: number; "page_size"?: number }): Promise<Array<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "body": string; "parent_id"?: number; "created_at": string; "replies"?: Array<unknown> }>> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.kind !== undefined) search.set("kind", String(p.kind));
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/comments/${source}/${slug}${suffix}`;
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
    return (await res.json()) as Array<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "body": string; "parent_id"?: number; "created_at": string; "replies"?: Array<unknown> }>;
  }

  /**
   * Post a comment on content
   * @see POST /comments/{source}/{slug}
   */
  async create_post_x_x(source: string, slug: string, params?: { body: { "kind": "anime" | "comic" | "novel"; "body": string; "parent_id"?: number } }): Promise<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "body": string; "parent_id"?: number; "created_at": string; "replies"?: Array<unknown> }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/comments/${source}/${slug}${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "body": string; "parent_id"?: number; "created_at": string; "replies"?: Array<unknown> };
  }

  /**
   * Recent community activity feed
   * @see GET /community/feed
   * Returns the most recent reviews, comments, and public list creations.
   * 
   * Results are merged and sorted by creation time, newest first.
   */
  async community(params?: { "limit"?: number; "kind"?: "anime" | "comic" | "novel" }): Promise<Array<{ "type": "review" | "comment" | "list"; "user_id": number; "username"?: string; "data": Record<string, unknown>; "created_at": string }>> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    if (p.kind !== undefined) search.set("kind", String(p.kind));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/community/feed${suffix}`;
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
    return (await res.json()) as Array<{ "type": "review" | "comment" | "list"; "user_id": number; "username"?: string; "data": Record<string, unknown>; "created_at": string }>;
  }

  /**
   * Browse Creators
   * @see GET /creator/browse
   * Browse all registered creators (public).
   */
  async browse(params?: { "limit"?: number; "offset"?: number }): Promise<Array<{ "id": number; "display_name": string; "avatar_url"?: string; "bio"?: string; "follower_count"?: number; "series_count"?: number; "verified"?: boolean }>> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    if (p.offset !== undefined) search.set("offset", String(p.offset));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/creator/browse${suffix}`;
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
    return (await res.json()) as Array<{ "id": number; "display_name": string; "avatar_url"?: string; "bio"?: string; "follower_count"?: number; "series_count"?: number; "verified"?: boolean }>;
  }

  /**
   * Browse Creator Detail
   * @see GET /creator/browse/{creator_id}
   * View a creator's public profile and their published series.
   */
  async browse_get(creator_id: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/browse/${creator_id}${suffix}`;
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
   * Browse Creator Series
   * @see GET /creator/browse/{creator_id}/series/{series_id}
   * View a public series and its published chapters.
   */
  async browse_get_x(creator_id: string, series_id: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/browse/${creator_id}/series/${series_id}${suffix}`;
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
   * Create Chapter
   * @see POST /creator/chapters
   * Upload a new chapter to a series owned by the authenticated creator.
   */
  async create_post_x_x_x_x_x(params?: { body: { "series_id": number; "title": string; "chapter_number": number; "content": string; "content_format"?: string; "published"?: boolean } }): Promise<{ "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/chapters${suffix}`;
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
    return (await res.json()) as { "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string };
  }

  /**
   * Delete Chapter
   * @see DELETE /creator/chapters/{chapter_id}
   * Delete a chapter.
   */
  async delete_delete_x_x_x(chapter_id: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/chapters/${chapter_id}${suffix}`;
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
    return (await res.json()) as unknown;
  }

  /**
   * Get My Chapter
   * @see GET /creator/chapters/{chapter_id}
   * Get a single chapter (must own the parent series).
   */
  async get_get_x_x_x_x_x_x_x_x(chapter_id: string): Promise<{ "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/chapters/${chapter_id}${suffix}`;
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
    return (await res.json()) as { "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string };
  }

  /**
   * Update Chapter
   * @see PUT /creator/chapters/{chapter_id}
   * Update chapter content or metadata.
   */
  async update_put_x_x(chapter_id: string, params?: { body: { "title"?: string; "chapter_number"?: number; "content"?: string; "content_format"?: string; "published"?: boolean } }): Promise<{ "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/chapters/${chapter_id}${suffix}`;
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
    return (await res.json()) as { "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string };
  }

  /**
   * Creator Dashboard
   * @see GET /creator/dashboard
   * Get creator dashboard with stats.
   */
  async creator(): Promise<{ "profile": { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }; "series_count": number; "total_chapters": number; "total_views": number; "total_followers": number; "revenue_estimate": number; "recent_series": Array<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }>; "top_chapters": Array<{ "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/dashboard${suffix}`;
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
    return (await res.json()) as { "profile": { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }; "series_count": number; "total_chapters": number; "total_views": number; "total_followers": number; "revenue_estimate": number; "recent_series": Array<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }>; "top_chapters": Array<{ "id": number; "series_id": number; "title": string; "chapter_number": number; "content"?: string; "content_format"?: string; "word_count"?: number; "views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> };
  }

  /**
   * Unfollow Creator
   * @see DELETE /creator/follow/{creator_id}
   * Unfollow a creator.
   */
  async unfollow(creator_id: string): Promise<{ "following": boolean; "follower_count": number }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/follow/${creator_id}${suffix}`;
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
    return (await res.json()) as { "following": boolean; "follower_count": number };
  }

  /**
   * Follow Creator
   * @see POST /creator/follow/{creator_id}
   * Follow a creator.
   */
  async follow(creator_id: string): Promise<{ "following": boolean; "follower_count": number }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/follow/${creator_id}${suffix}`;
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
    return (await res.json()) as { "following": boolean; "follower_count": number };
  }

  /**
   * My Following
   * @see GET /creator/followers
   * List creator IDs that the authenticated user follows.
   */
  async my(): Promise<Array<number>> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/followers${suffix}`;
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
    return (await res.json()) as Array<number>;
  }

  /**
   * Get My Profile
   * @see GET /creator/profile
   * Get the authenticated user's creator profile.
   */
  async get_get_x_x_x_x_x_x(): Promise<{ "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/profile${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string };
  }

  /**
   * Update My Profile
   * @see PUT /creator/profile
   * Update the authenticated user's creator profile.
   */
  async update_put(params?: { body: { "display_name"?: string; "bio"?: string; "social_links"?: Record<string, unknown> } }): Promise<{ "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/profile${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string };
  }

  /**
   * Upload Avatar
   * @see POST /creator/profile/avatar
   * Upload a creator avatar image.
   */
  async upload(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/profile/avatar${suffix}`;
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
    return (await res.json()) as unknown;
  }

  /**
   * Register Creator
   * @see POST /creator/register
   * Register the authenticated user as a creator.
   */
  async register_post(params?: { body: { "display_name": string; "bio"?: string; "social_links"?: Record<string, unknown> } }): Promise<{ "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/register${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "display_name": string; "bio"?: string; "avatar_url"?: string; "social_links"?: Record<string, unknown>; "follower_count"?: number; "total_views"?: number; "verified"?: boolean; "created_at": string };
  }

  /**
   * List My Series
   * @see GET /creator/series
   * List the authenticated creator's series.
   */
  async list_get_x_x_x_x_x(params?: { "kind"?: string; "limit"?: number; "offset"?: number }): Promise<Array<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }>> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.kind !== undefined) search.set("kind", String(p.kind));
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    if (p.offset !== undefined) search.set("offset", String(p.offset));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/creator/series${suffix}`;
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
    return (await res.json()) as Array<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }>;
  }

  /**
   * Create Series
   * @see POST /creator/series
   * Create a new series under the authenticated creator.
   */
  async create_post_x_x_x_x(params?: { body: { "title": string; "description"?: string; "kind": string; "cover_image"?: string } }): Promise<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/series${suffix}`;
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
    return (await res.json()) as { "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string };
  }

  /**
   * Delete Series
   * @see DELETE /creator/series/{series_id}
   * Delete a series and all its chapters.
   */
  async delete_delete_x_x(series_id: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/series/${series_id}${suffix}`;
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
    return (await res.json()) as unknown;
  }

  /**
   * Get My Series
   * @see GET /creator/series/{series_id}
   * Get a single series with its chapters.
   */
  async get_get_x_x_x_x_x_x_x(series_id: string): Promise<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/series/${series_id}${suffix}`;
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
    return (await res.json()) as { "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string };
  }

  /**
   * Update Series
   * @see PUT /creator/series/{series_id}
   * Update series metadata.
   */
  async update_put_x(series_id: string, params?: { body: { "title"?: string; "description"?: string; "kind"?: string; "cover_image"?: string; "status"?: string; "published"?: boolean } }): Promise<{ "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/series/${series_id}${suffix}`;
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
    return (await res.json()) as { "id": number; "creator_id": number; "title": string; "description"?: string; "kind": string; "cover_image"?: string; "status"?: string; "chapter_count"?: number; "total_views"?: number; "published"?: boolean; "created_at": string; "updated_at": string };
  }

  /**
   * Upload Cover
   * @see POST /creator/upload/cover
   * Upload a cover image for a series. Returns the URL to use in series create/update.
   */
  async upload_post(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/creator/upload/cover${suffix}`;
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
    return (await res.json()) as unknown;
  }

  /**
   * Report a client-side error
   * @see POST /errors
   * Called by the browser/Next.js error boundary when something blows up.
   * 
   * Cheap to call, rate-limited globally, and never raises — a downstream
   * error tracker that itself errors is worse than no tracker.
   */
  async report(params?: { body: { "message": string; "stack"?: string; "source"?: string; "severity"?: string; "extra"?: Record<string, unknown> } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/errors${suffix}`;
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
   * Handle Http Get
   * @see GET /graphql
   */
  async handle(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/graphql${suffix}`;
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
   * Handle Http Post
   * @see POST /graphql
   */
  async handle_post(): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/graphql${suffix}`;
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
   * List reading lists for the current user
   * @see GET /lists
   */
  async get_get_x_x(): Promise<Array<{ "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> }>> {
    const suffix = "";
    const url = `${this._client.baseUrl}/lists${suffix}`;
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
    return (await res.json()) as Array<{ "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> }>;
  }

  /**
   * Create a reading list
   * @see POST /lists
   */
  async create_post_x_x_x(params?: { body: { "name": string; "is_public"?: boolean } }): Promise<{ "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/lists${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> };
  }

  /**
   * Delete a reading list
   * @see DELETE /lists/{list_id}
   */
  async delete_delete_x(list_id: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/lists/${list_id}${suffix}`;
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
    return (await res.json()) as unknown;
  }

  /**
   * Get a single reading list
   * @see GET /lists/{list_id}
   */
  async get_get_x_x_x(list_id: string): Promise<{ "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/lists/${list_id}${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> };
  }

  /**
   * Update a reading list
   * @see PUT /lists/{list_id}
   */
  async update(list_id: string, params?: { body: { "name"?: string; "is_public"?: boolean } }): Promise<{ "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/lists/${list_id}${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "username"?: string; "name": string; "is_public": boolean; "created_at": string; "items"?: Array<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> };
  }

  /**
   * Add an item to a reading list
   * @see POST /lists/{list_id}/items
   */
  async add(list_id: string, params?: { body: { "source": string; "slug": string; "kind": "anime" | "comic" | "novel" } }): Promise<{ "id": number; "source": string; "slug": string; "kind": string; "added_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/lists/${list_id}/items${suffix}`;
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
    return (await res.json()) as { "id": number; "source": string; "slug": string; "kind": string; "added_at": string };
  }

  /**
   * Remove an item from a reading list
   * @see DELETE /lists/{list_id}/items/{item_id}
   */
  async remove(list_id: string, item_id: string): Promise<unknown> {
    const suffix = "";
    const url = `${this._client.baseUrl}/lists/${list_id}/items/${item_id}${suffix}`;
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
    return (await res.json()) as unknown;
  }

  /**
   * Og Image
   * @see GET /og
   * Generate a dynamic OG image for social sharing.
   */
  async og(params?: { "title"?: string; "kind"?: string; "source"?: string; "thumbnail"?: string }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.title !== undefined) search.set("title", String(p.title));
    if (p.kind !== undefined) search.set("kind", String(p.kind));
    if (p.source !== undefined) search.set("source", String(p.source));
    if (p.thumbnail !== undefined) search.set("thumbnail", String(p.thumbnail));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/og${suffix}`;
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
   * List original series
   * @see GET /originals
   * List published original series. Defaults to featured only.
   */
  async list_get_x_x_x_x(params?: { "featured"?: boolean; "content_type"?: string; "page"?: number; "page_size"?: number }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.featured !== undefined) search.set("featured", String(p.featured));
    if (p.content_type !== undefined) search.set("content_type", String(p.content_type));
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/originals${suffix}`;
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
   * Apply to become a Nakama Originals creator
   * @see POST /originals/apply
   * Submit a creator application. Requires JWT auth.
   */
  async apply(params?: { body: { "pen_name": string; "bio"?: string; "portfolio_url"?: string; "sample_work"?: string; "content_types": string } }): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/originals/apply${suffix}`;
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
   * Original series detail
   * @see GET /originals/{slug}
   * Get original series detail with chapter list.
   */
  async get_get_x_x_x_x_x(slug: string): Promise<{ "ok"?: boolean; "source"?: string; "data": unknown }> {
    const suffix = "";
    const url = `${this._client.baseUrl}/originals/${slug}${suffix}`;
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
   * Get AI-powered content recommendations
   * @see POST /recommendations
   * Returns similar titles based on TF-IDF vectorisation and cosine similarity over title, synopsis, and genres. Supply as much context (synopsis, genres) as possible for the best results. Results are cached in Redis for 1 hour.
   */
  async get_post(params?: { body: { "title": string; "kind": "anime" | "comic" | "novel"; "limit"?: number; "synopsis"?: string; "genres"?: Array<string> } }): Promise<{ "ok"?: boolean; "anchor": string; "kind": string; "recommendations": Array<{ "title": string; "slug"?: string; "source"?: string; "score": number; "thumbnail"?: string; "genres"?: Array<string> }>; "cached"?: boolean }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/recommendations${suffix}`;
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
    return (await res.json()) as { "ok"?: boolean; "anchor": string; "kind": string; "recommendations": Array<{ "title": string; "slug"?: string; "source"?: string; "score": number; "thumbnail"?: string; "genres"?: Array<string> }>; "cached"?: boolean };
  }

  /**
   * Get reviews for content
   * @see GET /reviews/{source}/{slug}
   */
  async get(source: string, slug: string, params?: { "kind"?: "anime" | "comic" | "novel"; "page"?: number; "page_size"?: number }): Promise<Array<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "rating": number; "body": string; "created_at": string }>> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.kind !== undefined) search.set("kind", String(p.kind));
    if (p.page !== undefined) search.set("page", String(p.page));
    if (p.page_size !== undefined) search.set("page_size", String(p.page_size));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/reviews/${source}/${slug}${suffix}`;
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
    return (await res.json()) as Array<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "rating": number; "body": string; "created_at": string }>;
  }

  /**
   * Submit a review for content
   * @see POST /reviews/{source}/{slug}
   */
  async create_post_x(source: string, slug: string, params?: { body: { "kind": "anime" | "comic" | "novel"; "rating": number; "body": string } }): Promise<{ "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "rating": number; "body": string; "created_at": string }> {
    const p: any = (params as any) ?? {};
    const suffix = "";
    const url = `${this._client.baseUrl}/reviews/${source}/${slug}${suffix}`;
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
    return (await res.json()) as { "id": number; "user_id": number; "username"?: string; "source": string; "slug": string; "kind": string; "rating": number; "body": string; "created_at": string };
  }

  /**
   * Get review stats for content
   * @see GET /reviews/{source}/{slug}/stats
   */
  async get_get(source: string, slug: string, params?: { "kind"?: "anime" | "comic" | "novel" }): Promise<{ "count": number; "avg_rating": number; "distribution": Record<string, unknown> }> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.kind !== undefined) search.set("kind", String(p.kind));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/reviews/${source}/${slug}/stats${suffix}`;
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
    return (await res.json()) as { "count": number; "avg_rating": number; "distribution": Record<string, unknown> };
  }

  /**
   * Source health scoreboard
   * @see GET /sources/health
   * Return per-source health from Redis/memory counters.
   * 
   * Without ``probe=true`` this is pure counter reads (fast). With
   * ``probe=true`` the API hits each source home once and updates the board.
   * 
   * Response also includes ``token_health`` for sources that require bearer
   * auth (currently komikcast). This lets dashboards flag expired tokens
   * before users hit empty chapter image lists.
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
   * Trending All
   * @see GET /trending
   * Get trending items across all kinds.
   */
  async trending_get(params?: { "limit"?: number }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/trending${suffix}`;
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
   * Popular Kind
   * @see GET /trending/popular/{kind}
   * Get all-time popular items for a specific kind.
   */
  async popular(kind: string, params?: { "limit"?: number }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/trending/popular/${kind}${suffix}`;
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
   * Trending Kind
   * @see GET /trending/{kind}
   * Get trending items for a specific kind.
   */
  async trending_get_x(kind: string, params?: { "limit"?: number }): Promise<unknown> {
    const p: any = (params as any) ?? {};
    const search = new URLSearchParams();
    if (p.limit !== undefined) search.set("limit", String(p.limit));
    const qs = search.toString();
    const suffix = qs ? `?${qs}` : "";
    const url = `${this._client.baseUrl}/trending/${kind}${suffix}`;
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
