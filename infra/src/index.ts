import { Container, getRandom } from "@cloudflare/containers";
import { getCacheTTL, buildCacheKey, applyCacheHeaders } from "./edge-cache";

// Stateless FastAPI proxy — load-balance across a small pool.
const INSTANCE_COUNT = 2;

// Cache API instance for edge caching (285+ locations worldwide)
// Falls back gracefully if Cache API is unavailable.
declare const caches: {
  default: Cache;
  open(name: string): Promise<Cache>;
};

export class NakamaContainer extends Container {
  // Must match the port uvicorn listens on in Dockerfile.cloudflare
  defaultPort = 8080;
  // Keep warm longer for scraper latency; still sleeps when idle.
  sleepAfter = "30m";
  // Scrapers need outbound internet.
  enableInternet = true;
  pingEndpoint = "/health";

  envVars = {
    OFFLINE_MODE: "0",
    CACHE_TTL_SECONDS: "900",
    RATE_LIMIT: "60/minute",
    REQUEST_TIMEOUT: "20",
    PORT: "8080",
  };

  override onStart(): void {
    console.log("Nakama container started");
  }

  override onStop(): void {
    console.log("Nakama container stopped");
  }

  override onError(error: unknown): void {
    console.error("Nakama container error:", error);
  }
}

export default {
  async fetch(
    request: Request,
    env: { NAKAMA: DurableObjectNamespace },
  ): Promise<Response> {
    const url = new URL(request.url);
    const ttl = getCacheTTL(url, request.method);

    // ── Edge cache: serve from cache if available ──────────
    if (ttl > 0 && request.method === "GET") {
      try {
        const cacheKey = buildCacheKey(request);
        const cache = await caches.open("nakama-edge");
        const cached = await cache.match(cacheKey);
        if (cached) {
          // Track cache hit
          console.log(`CACHE HIT: ${url.pathname}`);
          return cached;
        }
        console.log(`CACHE MISS: ${url.pathname}`);
      } catch {
        // Cache API unavailable — continue to origin
      }
    }

    // ── Origin: route to container ─────────────────────────
    const container = await getRandom(env.NAKAMA, INSTANCE_COUNT);
    let response = await container.fetch(request);

    // ── Store in edge cache ─────────────────────────────────
    if (ttl > 0 && response.ok && request.method === "GET") {
      try {
        const cacheKey = buildCacheKey(request);
        const cache = await caches.open("nakama-edge");
        // Clone before caching (response body can only be read once)
        const toCache = new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
        });
        // Store without awaiting — fire-and-forget for performance
        cache.put(cacheKey, toCache);
      } catch {
        // Cache put failed — non-critical
      }
    }

    // ── Apply cache headers ─────────────────────────────────
    response = applyCacheHeaders(response, ttl);

    return response;
  },
};
