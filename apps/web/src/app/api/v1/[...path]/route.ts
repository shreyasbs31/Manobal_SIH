import { type NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function engineOrigin(): string {
  const raw =
    process.env.ENGINE_INTERNAL_URL ?? process.env.NEXT_PUBLIC_ENGINE_URL ?? "http://localhost:8000";
  return raw.replace(/\/$/, "");
}

async function proxy(request: NextRequest, parts: string[]): Promise<Response> {
  const target = `${engineOrigin()}/api/v1/${parts.join("/")}${request.nextUrl.search}`;
  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) {
    headers.set("authorization", auth);
  }
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  const accept = request.headers.get("accept");
  if (accept) {
    headers.set("accept", accept);
  }
  const trace = request.headers.get("x-trace-id");
  if (trace) {
    headers.set("x-trace-id", trace);
  }
  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }
  try {
    const upstream = await fetch(target, init);
    const body = await upstream.arrayBuffer();
    const response = new NextResponse(body, { status: upstream.status });
    for (const key of ["content-type", "x-trace-id", "cache-control"]) {
      const value = upstream.headers.get(key);
      if (value) {
        response.headers.set(key, value);
      }
    }
    return response;
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "engine_unreachable",
          message: "The engine is not reachable from the web app.",
          hint: "Start the stack with make dev and keep port 8000 free.",
        },
      },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}
