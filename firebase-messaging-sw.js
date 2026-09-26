importScripts(
    "https://www.gstatic.com/firebasejs/12.4.0/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/12.4.0/firebase-messaging-compat.js"
);


firebase.initializeApp({
  apiKey: "AIzaSyDXX53l74j6x1xGT46o5WznQ9vDqs1feJM",
  authDomain: "friday-ec342.firebaseapp.com",
  projectId: "friday-ec342",
  storageBucket: "friday-ec342.firebasestorage.app",
  messagingSenderId: "254940506166",
  appId: "1:254940506166:web:a96bd839fd2d452ac29097",
  measurementId: "G-4905WK118P"
});


const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    // console.log("🔥 Background FCM:", payload);

    const title = payload.data?.title || "Friday";
    const body = payload.data?.body || "Jarvis Online, Sir";

    self.registration.showNotification(title, {
        body,
        icon: "/assets/Friday.png"
    });
});


const CACHE_NAME = "friday-v1";

const FILES_TO_CACHE = [
    "/",
    "/Google-Jarvis.html",
    "/manifest.json",
    "/assets/Friday.png"
];


// ===============================
// INSTALL
// ===============================

self.addEventListener("install", (event) => {

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(FILES_TO_CACHE))
    );

    self.skipWaiting();

});


// ===============================
// ACTIVATE
// ===============================

self.addEventListener("activate", (event) => {

    event.waitUntil(
        self.clients.claim()
    );

});


// ===============================
// FETCH
// ===============================

self.addEventListener("fetch", (event) => {

    event.respondWith(
        caches.match(event.request)
            .then((cached) => {
                return cached || fetch(event.request);
            })
    );

});