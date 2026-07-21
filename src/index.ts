import { Container, getRandom } from "@cloudflare/containers";

// Stateless FastAPI proxy — load-balance across a small pool.
const INSTANCE_COUNT = 2;

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
    // Route every request to a random warm container instance.
    // Use container.fetch() (not containerFetch) so WebSocket upgrades work.
    const container = await getRandom(env.NAKAMA, INSTANCE_COUNT);
    return container.fetch(request);
  },
};
