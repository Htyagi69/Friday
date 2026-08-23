
const CACHE_NAME='friday-v1'

const FILES_TO_CACHE=[
    "/",
    "Google-Jarvis.html",
    "manifest.json",
    "assets/Friday.png",
]

self.addEventListener('install',event=>{
    event.waitUntil(
        caches.open("CACHE_NAME")
        .then(cache=>cache.addAll(FILES_TO_CACHE))
    )
})

self.addEventListener('fetch',event=>{
     event.respondWith(
    caches.match(event.request)
      .then(cached => {
        return cached || fetch(event.request);
      })
  );
})