self.addEventListener("install", function(event) {

    event.waitUntil(

        caches.open("hangarin-cache-v1").then(function(cache) {

            return cache.addAll([
                "/",
                "/tasks/",
                "/static/taskmanager/style.css",
                "/static/taskmanager/img/icon-192x192.png"
            ]);

        })

    );

});


self.addEventListener("fetch", function(event) {

    event.respondWith(

        caches.match(event.request).then(function(response) {

            return response || fetch(event.request);

        })

    );

});