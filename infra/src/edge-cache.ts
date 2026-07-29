/**
 * Edge Cache Strategy for Nakama CDN.
 * 
 * Caches GET responses at Cloudflare's edge (285+ locations worldwide).
 * Dramatically reduces origin load and latency for static/heavy content:
 * - Search results (TTL 5 min)
 * - Detail pages (TTL 30 min)  
 * - Images (TTL 24 hours, proxied)
 * - Home page listings (TTL 2 min)
 * - OpenAPI spec (TTL 1 hour)
 * - Health endpoints (no cache)
 */

export interface CacheRule {
  /** URL path pattern (regex) */
  pattern: RegExp;
  /** Cache TTL in seconds */
  ttl: number;
  /** Cache key override (optional) */
  key?: (request: Request) => string;
  /** Whether to cache */
  cache: boolean;
}

export const CACHE_RULES: CacheRule[] = [
  // Health/status — never cache
  { pattern: /^\/(health|stats|sources\/health)/, ttl: 0, cache: false },
  
  // OpenAPI spec — 1 hour
  { pattern: /^\/openapi\.json/, ttl: 3600, cache: true },
  
  // Search — 5 minutes (results change but not instantly)
  { pattern: /^\/anime\/search|comic\/search|novel\/search|search/, ttl: 300, cache: true },
  
  // Detail pages — 30 minutes (metadata rarely changes)
  { pattern: /^\/(anime|comic|novel)\/[\w-]+\/detail/, ttl: 1800, cache: true },
  
  // Home listings — 2 minutes
  { pattern: /^\/(anime|comic|novel)\/home/, ttl: 120, cache: true },
  
  // Images — 24 hours with proxy
  { pattern: /^\/image\//, ttl: 86400, cache: true },
  
  // Chapter/episode content — 15 minutes
  { pattern: /^\/(anime|comic|novel)\/[\w-]+\/(episode|chapter)/, ttl: 900, cache: true },
  
  // Everything else — short TTL
  { pattern: /.*/, ttl: 60, cache: true },
];

/**
 * Determine cache TTL for a request.
 */
export function getCacheTTL(url: URL, method: string): number {
  // Only cache GET requests
  if (method !== "GET") return 0;
  
  const pathname = url.pathname;
  for (const rule of CACHE_RULES) {
    if (rule.pattern.test(pathname)) {
      return rule.cache ? rule.ttl : 0;
    }
  }
  return 0;
}

/**
 * Build cache key from request. Strips auth tokens and varying query params.
 */
export function buildCacheKey(request: Request): string {
  const url = new URL(request.url);
  // Normalize: remove auth tokens, sort query params
  url.searchParams.delete("token");
  url.searchParams.delete("api_key");
  url.searchParams.sort();
  return url.toString();
}

/**
 * Apply cache headers to response.
 */
export function applyCacheHeaders(
  response: Response,
  ttl: number
): Response {
  if (ttl <= 0) {
    response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate");
    response.headers.set("CDN-Cache-Control", "no-store");
    return response;
  }
  
  response.headers.set("Cache-Control", `public, max-age=${ttl}, s-maxage=${ttl}`);
  response.headers.set("CDN-Cache-Control", `public, max-age=${ttl}`);
  response.headers.set("Surrogate-Control", `public, max-age=${ttl}`);
  
  // Stale-while-revalidate: serve stale for 5% of TTL while revalidating
  const swr = Math.max(10, Math.floor(ttl * 0.05));
  response.headers.set("Cache-Control", 
    `public, max-age=${ttl}, s-maxage=${ttl}, stale-while-revalidate=${swr}`);
  
  return response;
}
