# Phase 10 — Frontend Polish, PWA & Static Assets

## Context

**Tablii** — Phase 10 of 12. Polish the UI, add remaining JS files, implement PWA, and create static assets.

---

## Deliverables

```
app/static/
├── js/
│   ├── waiter_calls.js       # Waiter call client JS
│   ├── menu_builder.js       # Dashboard menu drag-and-drop
│   ├── floor_map.js          # Table floor map editor
│   └── notifications.js      # Browser notification API
│
├── css/
│   └── input.css             # Extend existing with final styles
│
├── sounds/
│   ├── new_order.mp3         # Use any free notification sound (or create silence placeholder)
│   ├── order_ready.mp3
│   └── call_waiter.mp3
│
├── images/
│   ├── default_food.png      # Placeholder food image (generate or provide a gray plate icon)
│   └── logo.png              # Tablii logo
│
├── icons/                    # PWA icons (generate as solid orange squares with "T")
│   ├── icon-192.png
│   └── icon-512.png
│
├── manifest.json             # PWA manifest
└── sw.js                     # Service Worker
```

---

## JavaScript Files

### `waiter_calls.js`

```javascript
function callWaiter(slug, tableId, type, message = "") {
  // POST /r/{slug}/table/{tableId}/call-waiter
  // body: { call_type: type, message }
  // On success: show toast "Waiter has been called"
}

function showWaiterCall(data) {
  // Display incoming call notification for waiter
  // Show: table number, call type icon, message
  // Play call_waiter sound
  // Vibrate: navigator.vibrate([200, 100, 200])
}

function resolveCall(callId) {
  // POST /waiter/calls/{callId}/resolve
  // On success: remove call from UI
}
```

### `menu_builder.js`

```javascript
function initDragDropCategories() {
  // Enable drag-and-drop reordering of category rows.
  // On drop: POST /dashboard/menu/categories/reorder with new order.
}

function initDragDropItems() {
  // Enable drag-and-drop reordering of menu items.
}

function initImagePreview() {
  // Preview uploaded image in the menu item form before submission.
  // Read file with FileReader, display in <img> preview element.
}

function toggleAvailability(itemId) {
  // POST /dashboard/menu/item/{id}/toggle
  // Toggle switch UI without page reload.
}
```

### `floor_map.js`

```javascript
function renderFloorMap(canvasId, tables) {
  // Render tables as draggable rectangles on canvas.
  // Color by status: green (free), orange (occupied), red (reserved).
  // Show table number inside each rectangle.
}

function dragTable(tableId, newX, newY) {
  // Update table position during drag.
}

function saveFloorLayout(tables) {
  // POST updated positions to server.
}
```

### `notifications.js`

```javascript
function requestNotificationPermission() {
  // Request browser Notification API permission.
  if ("Notification" in window && Notification.permission === "default") {
    Notification.requestPermission();
  }
}

function showDesktopNotification(
  title,
  body,
  icon = "/static/images/logo.png",
) {
  if (Notification.permission === "granted") {
    new Notification(title, { body, icon });
  }
}

function vibratePhone(pattern = [200]) {
  if ("vibrate" in navigator) {
    navigator.vibrate(pattern);
  }
}
```

---

## PWA Files

### `manifest.json`

```json
{
  "name": "Tablii — Restaurant Ordering",
  "short_name": "Tablii",
  "description": "Scan, order, enjoy — digital restaurant experience",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#f97316",
  "orientation": "any",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

### `sw.js` — Service Worker

```javascript
const CACHE_NAME = "tablii-v1";
const urlsToCache = [
  "/",
  "/static/css/output.css",
  "/static/js/app.js",
  "/static/js/socket.js",
  "/static/images/logo.png",
  "/static/images/default_food.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache)),
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    }),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)),
        ),
      ),
  );
});
```

---

## CSS Polish (extend `input.css`)

Add the following layers to the existing Tailwind input file:

```css
@layer components {
  /* Status badges */
  .badge-new {
    @apply bg-blue-100 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full;
  }
  .badge-accepted {
    @apply bg-indigo-100 text-indigo-700 text-xs font-medium px-2 py-0.5 rounded-full;
  }
  .badge-preparing {
    @apply bg-yellow-100 text-yellow-700 text-xs font-medium px-2 py-0.5 rounded-full;
  }
  .badge-ready {
    @apply bg-green-100 text-green-700 text-xs font-medium px-2 py-0.5 rounded-full;
  }
  .badge-served {
    @apply bg-gray-100 text-gray-700 text-xs font-medium px-2 py-0.5 rounded-full;
  }
  .badge-cancelled {
    @apply bg-red-100 text-red-700 text-xs font-medium px-2 py-0.5 rounded-full;
  }

  /* Pulse animation for active orders */
  .pulse-dot {
    @apply relative;
  }
  .pulse-dot::before {
    content: "";
    @apply absolute w-3 h-3 bg-green-400 rounded-full animate-ping;
  }
}

@layer utilities {
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
}
```

After modifying `input.css`, run: `npm run build:css` to regenerate `output.css`.

---

## Sound Files

Create three minimal placeholder `.mp3` files (or provide instructions to generate them via a script). Each should be a short notification tone (< 2 seconds). If generating is not possible, create empty files and add a README note.

---

## Validation

- [ ] PWA installs on mobile Chrome.
- [ ] Service Worker caches core assets.
- [ ] Desktop notifications appear when permitted.
- [ ] Drag-and-drop works for categories and floor map.
- [ ] Image preview works in menu item form.
- [ ] Status badge classes render correctly.

## Strict Rules

1. Service Worker must NOT cache API/dynamic routes — only static assets.
2. Notification API: always check permission before creating.
3. All JS files must be purely functional — no global state except socket.
4. Sound files must be < 100KB each.
5. PWA icons must be square PNGs at specified sizes.
