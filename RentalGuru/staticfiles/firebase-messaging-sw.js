// firebase-messaging-sw.js

importScripts('https://www.gstatic.com/firebasejs/9.14.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.14.0/firebase-messaging-compat.js');

const firebaseConfig = {
  apiKey: "AIzaSyAVFtJ9isbDXFaLbmJJcDdpMA8jsl_ZyOU",
  authDomain: "rental-guru-465d7.firebaseapp.com",
  projectId: "rental-guru-465d7",
  storageBucket: "rental-guru-465d7.firebasestorage.app",
  messagingSenderId: "274995950667",
  appId: "1:274995950667:web:e3872098a2b49116acc9ce",
  measurementId: "G-K2WEZKWG2W"
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function (payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);

  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/firebase-logo.png' // путь к иконке
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});