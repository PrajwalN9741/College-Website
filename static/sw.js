const CACHE_NAME = 'admin-portal-v2';
const ASSETS = [
    '/admin',
    '/static/style.css',
    '/static/images/logo.png',
    '/manifest.json',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css'
];

self.addEventListener('install', (e) => {
    self.skipWaiting();
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
    );
});

self.addEventListener('activate', (e) => {
    e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
    // For API calls or non-GET requests, network only
    if (e.request.method !== 'GET' || e.request.url.includes('/api/')) {
        return;
    }

    e.respondWith(
        fetch(e.request)
            .catch(() => caches.match(e.request))
    );
});
