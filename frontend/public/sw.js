/* Nakama Service Worker — minimal offline cache.
 *
 * Strategy:
 * - Install: precache shell + offline page
 * - Fetch:
 *   • Same-origin JS/CSS/images: cache-first (immutable)
 *   • /api/ GET requests: network-first with 3s timeout, fall back to cache
 *   • Navigation requests: network-first, fall back to offline page
 * - Activate: clean up old caches
 *
 * This gives users basic offline support without disrupting live data.
 */

const VERSION = 'v2';
const CACHE_SHELL = `nakama-shell-${VERSION}`;
const CACHE_RUNTIME = `nakama-runtime-${VERSION}`;
const SHELL_URLS = ['/offline', '/manifest.json', '/icon-192.png', '/icon-512.png'];

// On install: cache the app shell
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_SHELL).then((cache) => cache.addAll(SHELL_URLS))
            .then(() => self.skipWaiting())
    );
});

// On activate: clean up old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k !== CACHE_SHELL && k !== CACHE_RUNTIME)
                    .map((k) => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

// Helper: timeout a fetch
function fetchWithTimeout(req, timeoutMs = 3000) {
    return new Promise((resolve, reject) => {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), timeoutMs);
        fetch(req, { signal: controller.signal })
            .then((res) => { clearTimeout(timeout); resolve(res); })
            .catch((err) => { clearTimeout(timeout); reject(err); });
    });
}

// On fetch: cache strategy
self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;

    const url = new URL(req.url);

    // Same-origin static: cache-first
    if (url.origin === location.origin && /\.(js|css|png|jpg|jpeg|svg|woff2?|ttf|ico)$/.test(url.pathname)) {
        event.respondWith(
            caches.match(req).then((cached) =>
                cached || fetch(req).then((res) => {
                    const copy = res.clone();
                    caches.open(CACHE_RUNTIME).then((c) => c.put(req, copy));
                    return res;
                })
            )
        );
        return;
    }

    // Same-origin navigation: network-first, fall back to offline page
    if (req.mode === 'navigate' && url.origin === location.origin) {
        event.respondWith(
            fetchWithTimeout(req, 3000)
                .then((res) => {
                    if (!res.ok) throw new Error('offline');
                    return res;
                })
                .catch(() => caches.match('/offline'))
        );
        return;
    }

    // Cross-origin / API: network-first, fall back to cache
    event.respondWith(
        fetchWithTimeout(req, 3000)
            .then((res) => {
                if (res.ok) {
                    const copy = res.clone();
                    caches.open(CACHE_RUNTIME).then((c) => c.put(req, copy));
                }
                return res;
            })
            .catch(() => caches.match(req))
    );
});
