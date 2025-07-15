// firebase-messaging-sw.js
// Используем compat версию для совместимости
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

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Retrieve Firebase Messaging object
const messaging = firebase.messaging();

// Background message handler
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);

  const notificationTitle = payload.notification?.title || 'Новое уведомление';
  const notificationOptions = {
    body: payload.notification?.body || 'У вас есть новое сообщение',
    icon: payload.notification?.icon || '/firebase-logo.png',
    badge: '/firebase-logo.png',
    tag: 'notification-1',
    requireInteraction: false,
    actions: [
      {
        action: 'open',
        title: 'Открыть'
      },
      {
        action: 'close',
        title: 'Закрыть'
      }
    ]
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', function(event) {
  console.log('[firebase-messaging-sw.js] Notification click received.');

  event.notification.close();

  if (event.action === 'open') {
    // Открываем приложение
    event.waitUntil(
      clients.openWindow('https://rentalguru.ru')
    );
  }
});