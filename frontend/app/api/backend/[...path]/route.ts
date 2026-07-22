import { NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

/**
 * Same-origin BFF proxy.
 *
 * Browser/client code can call `/api/backend/<path>` without ever seeing
 * API_KEY. The Next.js server attaches X-API-Key and forwards to the
 * internal FastAPI service.
 *
 * Allowed path prefixes only — no open proxy.
 */
export const dynamic = "force-dynamic";

const ALLOWED_PREFIXES = [
  "/anime",
  "/comic",
  "/novel",
  "/search",
  "/stats",
  "/health",
  "/docs.json",
  "/openapi.json",
  "/image",
  "/history",
  "/proxy",
];

function backendBase(): string {
  return (
    process.env.API_INTERNAL_URL?.replace(/\/$/, "") ||
    process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
    "http://localhost:8000"
  );
}

function isAllowed(path: string): boolean {
  if (path === "/" || path === "") return true;
  return ALLOWED_PREFIXES.some((p) => path === p || path.startsWith(p + "/"));
}

async function proxy(req: NextRequest, pathParts: string[]) {
  const subPath = "/" + (pathParts || []).map(decodeURIComponent).join("/");
  if (!isAllowed(subPath)) {
    return NextResponse.json(
      { ok: false, error: "Path not allowed via BFF proxy" },
      { status: 403 }
    );
  }

  const url = new URL(req.url);
  const target = `${backendBase()}${subPath}${url.search}`;
  const headers = new Headers();
  headers.set("Accept", req.headers.get("Accept") || "application/json");
  const key = process.env.API_KEY || "";
  if (key) headers.set("X-API-Key", key);

  // Forward content-type for non-GET if present
  const ct = req.headers.get("Content-Type");
  if (ct) headers.set("Content-Type", ct);

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch (e) {
    return NextResponse.json(
      {
        ok: false,
        error: "Upstream unreachable",
        detail: e instanceof Error ? e.message : String(e),
      },
      { status: 502 }
    );
  }

  const outHeaders = new Headers();
  const pass = ["content-type", "cache-control"];
  for (const h of pass) {
    const v = upstream.headers.get(h);
    if (v) outHeaders.set(h, v);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}

type Ctx = { params: { path?: string[] } };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
