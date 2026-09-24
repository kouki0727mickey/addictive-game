/* ORBIT SWITCH service worker: play offline after the first visit.
 * Stale-while-revalidate: serve from cache instantly, refresh the cache in the background,
 * so a new deploy is picked up on the next launch without ever blocking on the network. */
const CACHE = 'orbit-switch-v2';
const SHELL = ['./', 'index.html', 'css/style.css', 'js/i18n.js', 'js/core.js', 'js/meta.js', 'js/audio.js', 'js/main.js', 'icon.svg', 'manifest.webmanifest'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  e.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(req, { ignoreSearch: true }).then((hit) => {
        const fresh = fetch(req)
          .then((res) => {
            if (res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => hit);
        if (hit) {
          e.waitUntil(fresh);
          return hit;
        }
        return fresh;
      })
    )
  );
});
