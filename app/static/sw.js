/**
 * sw.js — Tablii Service Worker
 *
 * Strategy: cache-first for static assets, network-first for everything else.
 * NEVER caches API or dynamic Flask routes.
 */

'use strict';

const CACHE_NAME = 'tablii-v1';

// Only static, immutable assets — NO Flask routes, NO /dashboard, NO /r/ paths
const STATIC_ASSETS = [
  '/static/css/output.css',
  '/static/js/app.js',
  '/static/js/socket.js',
  '/static/js/cart.js',
  '/static/js/order_tracking.js',
  '/static/js/waiter_calls.js',
  '/static/js/notifications.js',
  '/static/images/logo.png',
  '/static/images/default_food.png',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/manifest.json',
];

// ── Install ────────────────────────────────────────────────────────────────

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Use individual adds so one failure doesn't block everything
      return Promise.allSettled(
        STATIC_ASSETS.map(url => cache.add(url).catch(() => {/* log silently */}))
      );
    })
  );
  self.skipWaiting();
});

// ── Activate ───────────────────────────────────────────────────────────────

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(
        names
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch ──────────────────────────────────────────────────────────────────

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Only handle same-origin GET requests
  if (event.request.method !== 'GET' || url.origin !== location.origin) {
    return;  // Let browser handle POST / cross-origin as normal
  }

  // Skip dynamic routes — let Flask SSR them fresh every time
  const isDynamic =
    url.pathname.startsWith('/dashboard') ||
    url.pathname.startsWith('/r/') ||
    url.pathname.startsWith('/cashier') ||
    url.pathname.startsWith('/kitchen') ||
    url.pathname.startsWith('/waiter') ||
    url.pathname.startsWith('/login') ||
    url.pathname.startsWith('/register') ||
    url.pathname.startsWith('/payment') ||
    url.pathname === '/';

  if (isDynamic) {
    return;  // Network only for all Flask-rendered pages
  }

  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
