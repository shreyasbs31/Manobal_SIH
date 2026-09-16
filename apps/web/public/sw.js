const CACHE = "manobal-saathi-v1";
const PRECACHE = [
  "/app",
  "/app/check-in",
  "/app/safety",
  "/app/toolkit",
  "/app/toolkit/breathe",
  "/app/plan",
  "/app/me",
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
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") {
    return;
  }
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request)
        .then((response) => {
          const copy = response.clone();
          if (response.ok && request.url.startsWith(self.location.origin)) {
            void caches.open(CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => cached || caches.match("/app/safety"));
    }),
  );
});
