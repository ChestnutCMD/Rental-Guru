console.log('[Firebase SW] Service Worker начал загрузку');

const CACHE_NAME = 'firebase-messaging-v1';
const FIREBASE_VERSION = '9.14.0';

self.addEventListener('install', (event) => {
  console.log('[Firebase SW] Установка Service Worker');
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  console.log('[Firebase SW] Активация Service Worker');
  event.waitUntil(self.clients.claim());
});

// Основная логика Firebase Messaging
try {
  importScripts(
    `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-app-compat.js`,
    `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}/firebase-messaging-compat.js`
  );

      const firebaseConfig = {
      apiKey: "AIzaSyBBecGpIXjG5gEdk7KbpxUd-kAZM0a_Hes",
      authDomain: "rental-guru-6ed62.firebaseapp.com",
      projectId: "rental-guru-6ed62",
      storageBucket: "rental-guru-6ed62.appspot.com",
      messagingSenderId: "120690662784",
      appId: "1:120690662784:web:bc8ab9e83770e472aeb565",
      measurementId: "G-7XY2SZNXZW"
    };

  if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
    console.log('[Firebase SW] Firebase инициализирован');
  }

  const messaging = firebase.messaging();

  // Обработка фоновых сообщений
  messaging.onBackgroundMessage((payload) => {
    console.log('[Firebase SW] Получено фоновое сообщение', payload);

    const notificationTitle = payload.notification?.title || 'Новое уведомление';
    const notificationOptions = {
      body: payload.notification?.body || '',
      icon: payload.notification?.icon || '/static/firebase-logo.png',
      data: payload.data || {}
    };

    return self.registration.showNotification(notificationTitle, notificationOptions);
  });

} catch (error) {
  console.error('[Firebase SW] Ошибка инициализации Firebase:', error);
}

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const urlToOpen = new URL(event.notification.data.url || 'https://rentalguru.ru', self.location.origin).href;

  event.waitUntil(
    clients.matchAll({type: 'window'}).then((windowClients) => {
      const matchingClient = windowClients.find((client) =>
        client.url === urlToOpen || client.url.startsWith(urlToOpen)
      );

      if (matchingClient) {
        return matchingClient.focus();
      } else {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

console.log('[Firebase SW] Service Worker загружен');