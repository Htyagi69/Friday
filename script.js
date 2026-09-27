import { initializeApp } from "https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js";

import {
    getMessaging,
    getToken,
    onMessage
} from "https://www.gstatic.com/firebasejs/12.4.0/firebase-messaging.js";


const firebaseConfig = {
  apiKey: "AIzaSyDXX53l74j6x1xGT46o5WznQ9vDqs1feJM",
  authDomain: "friday-ec342.firebaseapp.com",
  projectId: "friday-ec342",
  storageBucket: "friday-ec342.firebasestorage.app",
  messagingSenderId: "254940506166",
  appId: "1:254940506166:web:a96bd839fd2d452ac29097",
  measurementId: "G-4905WK118P"
};



const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

const registration =
    await navigator.serviceWorker.register("/firebase-messaging-sw.js");

await new Promise((resolve, reject) => {
    if (registration.active?.state === "activated") {
        resolve();
        return;
    }

    const worker = registration.installing || registration.waiting || registration.active;

    if (!worker) {
        reject(new Error("No service worker found"));
        return;
    }

    worker.addEventListener("statechange", () => {
        console.log("🔥 SW state:", worker.state);

        if (worker.state === "activated") {
            resolve();
        }
    });
});

console.log("🔥 FCM Service Worker ACTIVATED");
// console.log("Script:",registration.active?.scriptURL);

const permission=await Notification.requestPermission();

console.log("Notification permission:", permission);

if(permission==="granted"){
      console.log("Notification permission granted");
      const token=await getToken(messaging,{
         vapidKey: "BHeElUz3rChHIJTwCsdL5H8rbVsmGZgXbpSmJxwTANdDARlendA_TsaCsdg9IWK8ikVyT3GPamItTARYVpac2lk",
        serviceWorkerRegistration: registration
      });
    //    console.log("FCM TOKEN:", token);
       if(token){
        // await fetch("http://127.0.0.1:8000/register-device",{
        await fetch("https://friday-exny.onrender.com/register-device",{
            method:"POST",
            headers:{
                "Content-Type":"application/json",
            },
            body:JSON.stringify({
                token:token
            })
        })
       }
}


function speak(text) {
    if (!("speechSynthesis" in window)) {
        console.log("Speech synthesis not supported");
        return;
    }

    // Stop any previous speech
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    utterance.lang = "en-IN";
    utterance.rate = 0.95;
    utterance.pitch = 0.85;
    utterance.volume = 1;

    speechSynthesis.speak(utterance);
}

onMessage(messaging, (payload) => {
    // console.log("🔥 Foreground message:", payload);

    const title = payload.data?.title || payload.notification?.title || "Friday";
    const body = payload.data?.body || payload.notification?.body || "No body";

    new Notification(title, {
        body: body,
        icon: "/assets/Friday.png"
    });
    speak(`${title}. ${body}`)
});

async function testNotification(){
    // const response=await fetch("http://127.0.0.1:8000/test-notify",{
    const response=await fetch("https://friday-exny.onrender.com/test-notify",{
        method:"POST",
    })
    const result=await response.json();
    // console.log("🔔 Test notification:", result);
}

window.testNotification = testNotification;
