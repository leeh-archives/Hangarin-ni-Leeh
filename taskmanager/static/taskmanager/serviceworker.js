self.addEventListener("install", function(event) {

    event.waitUntil(

        caches.open("hangarin-cache-v2").then(function(cache) {

            return cache.addAll([
                "/static/taskmanager/style.css",
                "/static/taskmanager/img/icon-192x192.png"
            ]);

        })

    );

});


self.addEventListener("fetch", function(event) {

    event.respondWith(

        fetch(event.request).catch(function() {

            return caches.match(event.request);

        })

    );

});