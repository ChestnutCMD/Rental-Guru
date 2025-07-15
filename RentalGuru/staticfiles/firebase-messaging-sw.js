// firebase-messaging-sw.js
// Production-ready Service Worker для Firebase Cloud Messaging

console.log('[firebase-messaging-sw.js] Начинаем загрузку Service Worker');

// Проверяем доступность importScripts
if (typeof importScripts === 'function') {
    try {
        console.log('[firebase-messaging-sw.js] Загружаем Firebase SDK...');
        // Импортируем Firebase SDK (используем compat версию)
        importScripts('https://www.gstatic.com/firebasejs/9.14.0/firebase-app-compat.js');
        importScripts('https://www.gstatic.com/firebasejs/9.14.0/firebase-messaging-compat.js');

        // Проверяем, что Firebase загружен
        if (typeof firebase !== 'undefined') {
            console.log('Firebase SDK загружен успешно');

            const firebaseConfig = {
                apiKey: "AIzaSyAVFtJ9isbDXFaLbmJJcDdpMA8jsl_ZyOU",
                authDomain: "rental-guru-465d7.firebaseapp.com",
                projectId: "rental-guru-465d7",
                storageBucket: "rental-guru-465d7.firebasestorage.app",
                messagingSenderId: "274995950667",
                appId: "1:274995950667:web:e3872098a2b49116acc9ce",
                measurementId: "G-K2WEZKWG2W"
            };

            // Инициализируем Firebase
            try {
                firebase.initializeApp(firebaseConfig);
                console.log('Firebase инициализирован успешно');

                // Получаем объект messaging
                const messaging = firebase.messaging();

                // Обработчик фоновых сообщений
                messaging.onBackgroundMessage(function(payload) {
                    console.log('[firebase-messaging-sw.js] Получено фоновое сообщение:', payload);

                    // Извлекаем данные уведомления
                    const title = payload.notification?.title || payload.data?.title || 'Новое уведомление';
                    const body = payload.notification?.body || payload.data?.body || 'У вас есть новое сообщение';
                    const icon = payload.notification?.icon || payload.data?.icon || '/static/firebase-logo.png';

                    const notificationOptions = {
                        body: body,
                        icon: icon,
                        badge: '/static/firebase-logo.png',
                        tag: 'rental-guru-notification',
                        requireInteraction: false,
                        silent: false,
                        timestamp: Date.now(),
                        data: payload.data || {},
                        actions: [
                            {
                                action: 'open',
                                title: 'Открыть',
                                icon: '/static/open-icon.png'
                            },
                            {
                                action: 'close',
                                title: 'Закрыть',
                                icon: '/static/close-icon.png'
                            }
                        ]
                    };

                    // Показываем уведомление
                    return self.registration.showNotification(title, notificationOptions);
                });

                console.log('Обработчик фоновых сообщений установлен');

            } catch (initError) {
                console.error('Ошибка инициализации Firebase:', initError);
            }

        } else {
            console.error('Firebase SDK не загружен');
        }

    } catch (importError) {
        console.error('Ошибка импорта Firebase SDK:', importError);
    }
} else {
    console.error('importScripts не поддерживается');
}

// Обработчик клика по уведомлению
self.addEventListener('notificationclick', function(event) {
    console.log('[firebase-messaging-sw.js] Клик по уведомлению');

    // Закрываем уведомление
    event.notification.close();

    // Обрабатываем действие
    if (event.action === 'close') {
        return;
    }

    // Открываем/фокусируем приложение
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        }).then(function(clientList) {
            // Ищем уже открытое окно
            for (const client of clientList) {
                if (client.url.includes('rentalguru.ru') && 'focus' in client) {
                    return client.focus();
                }
            }

            // Если окно не найдено, открываем новое
            if (clients.openWindow) {
                const targetUrl = event.notification.data?.url || 'https://rentalguru.ru';
                return clients.openWindow(targetUrl);
            }
        })
    );
});

// Обработчик закрытия уведомления
self.addEventListener('notificationclose', function(event) {
    console.log('[firebase-messaging-sw.js] Уведомление закрыто');
});

// Обработчик активации Service Worker
self.addEventListener('activate', function(event) {
    console.log('[firebase-messaging-sw.js] Service Worker активирован');

    // Берем контроль над всеми клиентами
    event.waitUntil(
        self.clients.claim()
    );
});

// Обработчик установки Service Worker
self.addEventListener('install', function(event) {
    console.log('[firebase-messaging-sw.js] Service Worker установлен');

    // Активируем немедленно
    event.waitUntil(
        self.skipWaiting()
    );
});

// Обработчик ошибок
self.addEventListener('error', function(event) {
    console.error('[firebase-messaging-sw.js] Ошибка Service Worker:', event.error);
});

// Обработчик необработанных отклонений промисов
self.addEventListener('unhandledrejection', function(event) {
    console.error('[firebase-messaging-sw.js] Необработанное отклонение промиса:', event.reason);
});

console.log('[firebase-messaging-sw.js] Service Worker загружен');