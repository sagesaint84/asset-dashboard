// Wealth Service Worker - MDN Progressive Web App Standard
const CACHE_NAME = "wealth-cache-v43";
const PRECACHE_RESOURCES = [
  "/",
  "/dashboard",
  "/manifest.json",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/static/apple-touch-icon.png"
];

// 1. 서비스 워커 설치: 필수 리소스 사전 캐싱 (오프라인 지원)
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_RESOURCES))
      .then(() => self.skipWaiting())
      .catch((err) => {
        console.warn("[PWA SW] Pre-cache failed, continuing without precache:", err);
        return self.skipWaiting();
      })
  );
});

// 2. 서비스 워커 활성화: 이전 버전 캐시 정리
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// 3. 네트워크 요청 처리: Network-first 전략 (오프라인 시 캐시 반환)
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // API 요청 및 비GET 요청은 서비스 워커 캐시를 거치지 않고 실시간 처리
  if (url.pathname.startsWith("/api/") || event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // 정상 응답인 경우 정적 파일 캐시 최신화
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      })
      .catch(async () => {
        // 네트워크 단절/오프라인 시 캐시 리소스 반환
        const cachedResponse = await caches.match(event.request);
        if (cachedResponse) {
          return cachedResponse;
        }
        // 페이지 이동(navigation) 요청이면 메인 페이지 반환
        if (event.request.mode === "navigate") {
          const fallback = await caches.match("/");
          if (fallback) return fallback;
          const fallbackDash = await caches.match("/dashboard");
          if (fallbackDash) return fallbackDash;
        }
        return new Response("오프라인 상태입니다. 네트워크 연결을 확인하세요.", {
          status: 503,
          statusText: "Service Unavailable",
          headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
      })
  );
});

