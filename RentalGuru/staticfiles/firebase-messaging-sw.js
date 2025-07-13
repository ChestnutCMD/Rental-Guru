// firebase-messaging-sw.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-app.js";
import { getMessaging } from "https://www.gstatic.com/firebasejs/9.6.1/firebase-messaging-sw.js";

const firebaseConfig = {
  apiKey: "AIzaSyAVFtJ9isbDXFaLbmJJcDdpMA8jsl_ZyOU",
  authDomain: "rental-guru-465d7.firebaseapp.com",
  projectId: "rental-guru-465d7",
  storageBucket: "rental-guru-465d7.firebasestorage.app",
  messagingSenderId: "274995950667",
  appId: "1:274995950667:web:e3872098a2b49116acc9ce",
  measurementId: "G-K2WEZKWG2W"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// background handler
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/firebase-logo.png'
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});