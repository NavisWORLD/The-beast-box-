const CACHE = 'beastbox-web-v4';
const ASSETS = ['./', './index.html', './styles.css', './app.js', './policy.js', './profiles.js', './manifest.webmanifest', './icon.svg'];
const assetURLs = new Set(ASSETS.map(path => new URL(path, self.location.href).href));
const shellURLs = new Set(['./', './index.html'].map(path => new URL(path, self.location.href).href));

self.addEventListener('install', event => event.waitUntil(
  caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
));
self.addEventListener('activate', event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('beastbox-web-') && key !== CACHE)
    .map(key => caches.delete(key)))).then(() => self.clients.claim())
));
self.addEventListener('fetch', event => {
  const request = event.request;
  // Runtime data, health checks, errors, and arbitrary URLs never enter this cache.
  if (request.method !== 'GET' || !assetURLs.has(request.url)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    if (shellURLs.has(request.url)) {
      // A live shell response renews the HttpOnly session after a host restart.
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put(request, response.clone());
        return response;
      } catch (error) {
        const cached = await cache.match(request);
        if (cached) return cached;
        throw error;
      }
    }
    const cached = await cache.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  })());
});
