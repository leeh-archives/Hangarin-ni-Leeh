// Service worker for Hangarin (installable app + offline fallback).
// Pages always come from the network so your tasks are never stale.
// If the network is gone, people see a friendly offline page instead of an error.

const CACHE = "hangarin-cache-v4";
const FILES = [
    "/offline/",
    "/static/taskmanager/style.css",
    "/static/taskmanager/img/icon-192x192.png",
    "/static/taskmanager/img/icon-512x512.png",
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE).then(function (cache) {
            return cache.addAll(FILES);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(
                names
                    .filter(function (name) { return name !== CACHE; })
                    .map(function (name) { return caches.delete(name); })
            );
        })
    );
});

self.addEventListener("fetch", function (event) {
    // form posts and anything that isn't a plain GET go straight through
    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        fetch(event.request).catch(function () {
            return caches.match(event.request).then(function (cached) {
                if (cached) {
                    return cached;
                }
                if (event.request.mode === "navigate") {
                    return caches.match("/offline/");
                }
                return Response.error();
            });
        })
    );
});
