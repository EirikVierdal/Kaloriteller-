const CACHE_NAME = 'kaloriteller-cache-v1';
const urlsToCache = [
    '/',
    '/index',
    '/static/style.css',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(urlsToCache);
        })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request).then(function(response) {
            return response || fetch(event.request);
        })
    );
});
