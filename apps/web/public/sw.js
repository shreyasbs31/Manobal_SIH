const CACHE = "manobal-saathi-v11";
const PRECACHE = [
  "/app",
  "/app/check-in",
  "/app/safety",
  "/app/toolkit",
  "/app/toolkit/breathe",
  "/app/plan",
  "/app/me",
  "/app/saathi",
  "/app/assessments",
  "/app/assessments/pss10",
  "/app/onboarding",
  "/app/talk",
  "/app/rest",
  "/audio/safety.en.wav",
  "/audio/safety.hi.wav",
  "/audio/safety.ta.wav",
  "/audio/grounding.en.wav",
  "/audio/grounding.hi.wav",
  "/audio/breathing.en.wav",
  "/audio/breathing.hi.wav",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE);
      await Promise.allSettled(PRECACHE.map((url) => cache.add(url)));
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)));
      await self.clients.claim();
    })(),
  );
});

function pathCandidates(pathname) {
  const trimmed = pathname.replace(/\/+$/, "") || "/";
  const withSlash = trimmed === "/" ? "/" : `${trimmed}/`;
  return [...new Set([pathname, trimmed, withSlash])];
}

function isRscRequest(request) {
  if (request.headers.get("RSC") === "1") {
    return true;
  }
  if (request.headers.get("Next-Router-Prefetch")) {
    return true;
  }
  const url = new URL(request.url);
  return url.searchParams.has("_rsc");
}

function isHtmlResponse(response) {
  const type = (response.headers.get("content-type") || "").toLowerCase();
  return type.includes("text/html");
}

async function matchHtml(cache, key) {
  const hit = await cache.match(key);
  if (hit && isHtmlResponse(hit)) {
    return hit;
  }
  return undefined;
}

async function fromCache(request) {
  const cache = await caches.open(CACHE);
  const url = new URL(request.url);
  const navigate = request.mode === "navigate" || request.destination === "document";
  if (navigate) {
    const exact = await matchHtml(cache, request);
    if (exact) {
      return exact;
    }
    for (const path of pathCandidates(url.pathname)) {
      const hit = await matchHtml(cache, path);
      if (hit) {
        return hit;
      }
      const asRequest = await matchHtml(cache, new Request(path));
      if (asRequest) {
        return asRequest;
      }
    }
    return undefined;
  }
  const exact = await cache.match(request, { ignoreSearch: !isRscRequest(request) });
  if (exact) {
    return exact;
  }
  for (const path of pathCandidates(url.pathname)) {
    const hit = await cache.match(path, { ignoreSearch: true });
    if (hit) {
      return hit;
    }
    const asRequest = await cache.match(new Request(path), { ignoreSearch: true });
    if (asRequest) {
      return asRequest;
    }
  }
  return undefined;
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") {
    return;
  }
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    return;
  }
  const navigate = request.mode === "navigate" || request.destination === "document";
  event.respondWith(
    (async () => {
      try {
        const response = await fetch(request);
        const cacheable =
          url.pathname.startsWith("/app") ||
          url.pathname.startsWith("/audio/") ||
          url.pathname.startsWith("/worklets/") ||
          url.pathname.startsWith("/_next/static/") ||
          url.pathname === "/manifest.webmanifest";
        if (response.ok && cacheable && !isRscRequest(request)) {
          const cache = await caches.open(CACHE);
          await cache.put(request, response.clone());
          if (navigate && isHtmlResponse(response)) {
            await cache.put(new Request(url.pathname), response.clone());
            for (const path of pathCandidates(url.pathname)) {
              await cache.put(path, response.clone());
            }
          }
        }
        return response;
      } catch {
        const cached = await fromCache(request);
        if (cached) {
          return cached;
        }
        if (navigate) {
          for (const fallback of pathCandidates(url.pathname)) {
            const named = await fromCache(new Request(fallback));
            if (named) {
              return named;
            }
          }
          const safety = await fromCache(new Request("/app/safety"));
          if (url.pathname.startsWith("/app/safety") && safety) {
            return safety;
          }
          const home = await fromCache(new Request("/app"));
          if (home) {
            return home;
          }
          if (safety) {
            return safety;
          }
        }
        return new Response("Offline", { status: 503, statusText: "Offline" });
      }
    })(),
  );
});
