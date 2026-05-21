# Frontend Report

This report covers the Tablii frontend: structure, pages, templates, styling, JavaScript behavior, realtime UI, PWA support, and how the frontend communicates with the backend.

## Executive Summary

Tablii uses a server-rendered frontend built with Jinja templates, Tailwind CSS, vanilla JavaScript, Socket.IO, and a small PWA layer. The UI is split by user type:

- Public landing and authentication pages.
- Customer QR menu experience.
- Owner dashboard.
- Staff workstations for cashier, kitchen, and waiter.
- Super admin panel.
- Onboarding and subscription screens.

The frontend is intentionally practical for restaurant operations. Customer pages are mobile-first and table-scanning oriented. Staff pages prioritize live order visibility and quick actions. Owner/admin pages use denser dashboard layouts for management tasks.

## Frontend Stack

| Layer | Technology | Why it is used |
| --- | --- | --- |
| Template rendering | Jinja2 | Uses Flask server data directly and keeps pages simple without a separate SPA build |
| Styling | Tailwind CSS | Fast utility styling with a shared design token layer |
| Custom CSS | `app/static/css/input.css`, inline page variables | Defines reusable components and page-specific themes |
| JavaScript | Vanilla JS | Keeps interactivity light and avoids a heavy frontend framework |
| Realtime | Socket.IO client | Live orders, kitchen updates, waiter calls, customer tracking |
| Charts | Chart.js CDN | Dashboard analytics visualizations |
| PWA | `manifest.json`, `sw.js` | Installable app shell and static asset caching |
| Fonts | Google Fonts | Brand typography for dashboard, customer, and staff surfaces |

## Frontend File Structure

```text
app/templates/
  base.html                         Global public/customer base
  landing.html                      Public marketing page
  auth/                             Login and registration
  onboarding/                       Plan, payment, confirmation flow
  customer/                         QR menu, cart, checkout, tracking, review
  dashboard/                        Owner dashboard and management screens
  cashier/                          Cashier workstation
  kitchen/                          Kitchen display
  waiter/                           Waiter profile and tables
  admin/                            Super admin platform panel
  components/                       Reusable template fragments

app/static/
  css/input.css                     Tailwind source and component classes
  css/output.css                    Compiled CSS
  css/admin-theme.css               Admin-specific styling
  js/                               Frontend behavior modules
  images/                           Static images and upload output
  icons/                            PWA icons
  sounds/                           Realtime notification sounds
  manifest.json                     PWA manifest
  sw.js                             Service worker
```

## Template Architecture

### Global Base

File:

```text
app/templates/base.html
```

Responsibilities:

- Loads compiled Tailwind CSS.
- Loads Google Fonts.
- Defines viewport, CSRF meta tag, PWA manifest, theme color, and app icons.
- Renders global flash messages.
- Loads Socket.IO, `app.js`, and `notifications.js`.
- Registers the service worker.
- Exposes `{% block head %}`, `{% block content %}`, and `{% block scripts %}`.

Why this matters:

The base template keeps common browser setup in one place. Most pages inherit the same asset loading, CSRF token access, flash behavior, and PWA setup.

### Customer Base

File:

```text
app/templates/customer/base_customer.html
```

Responsibilities:

- Creates a mobile app shell with a sticky restaurant header.
- Displays restaurant logo/name and table number.
- Provides language switching for French, Arabic, and English.
- Reserves a bottom navigation/action area for cart and checkout actions.

Why this matters:

The customer experience is QR-first and phone-first. A contained `max-w-lg` shell makes it feel like a focused mobile ordering app even in a browser.

### Dashboard Base

File:

```text
app/templates/dashboard/base_dashboard.html
```

Responsibilities:

- Provides owner dashboard navigation.
- Defines dashboard-specific CSS variables and component classes.
- Displays the active restaurant/location.
- Provides the compact location switcher.
- Loads Socket.IO and dashboard notification scripts.

Why this matters:

Owner pages need consistent navigation, tenant context, and quick switching between locations. The base dashboard is the visual and structural frame for those workflows.

### Staff Bases

Files:

```text
app/templates/cashier/base_cashier.html
app/templates/kitchen/display.html
app/templates/waiter/tables.html
```

Responsibilities:

- Build role-specific workstations.
- Connect each role to Socket.IO rooms.
- Provide quick action buttons for order or table state changes.
- Use large, high-contrast operational layouts.

Why this matters:

Staff interfaces are used under time pressure. They need clear status, large touch targets, and realtime feedback more than decorative complexity.

### Admin Base

File:

```text
app/templates/admin/base_admin.html
```

Responsibilities:

- Provides super admin navigation and layout.
- Loads `admin-theme.css`.
- Separates platform management UI from restaurant owner UI.

Why this matters:

Super admin actions affect multiple tenants, so the interface needs a separate context and visual boundary.

## Page Groups

| Group | Templates | Primary user |
| --- | --- | --- |
| Landing | `landing.html` | Public visitors |
| Authentication | `auth/login.html`, `auth/register.html` | Owners and staff |
| Onboarding | `onboarding/plans.html`, `payment.html`, `confirmation.html` | Owners |
| Customer | `customer/menu.html`, `cart.html`, `checkout.html`, `order_tracking.html`, `call_waiter.html`, `review.html` | Restaurant guests |
| Owner dashboard | `dashboard/overview.html`, `locations.html`, `subscription.html`, `settings.html`, `reviews.html` | Managers |
| Menu management | `dashboard/menu/*.html` | Managers |
| Table management | `dashboard/tables/list.html` | Managers |
| Staff management | `dashboard/staff/*.html` | Managers |
| Analytics | `dashboard/analytics/reports.html` | Managers |
| Cashier | `cashier/orders.html`, `manual_order.html`, `profile.html` | Cashiers |
| Kitchen | `kitchen/display.html`, `profile.html` | Kitchen staff |
| Waiter | `waiter/tables.html`, `profile.html` | Waiters |
| Admin | `admin/*.html` | Super admins |

## Design System

### Color System

The Tailwind config extends these custom palettes:

| Palette | Use |
| --- | --- |
| `amber` | Primary brand/action warmth |
| `cream` | Light surfaces and customer backgrounds |
| `charcoal` | Dark app shell and text |
| `burgundy` | Rich accent states |
| `emerald` | Success and ready states |
| `sapphire` | Informational/new states |
| `ruby` | Danger/error states |
| `topaz` | Warning/preparing states |

Dashboard pages also define CSS custom properties such as:

```text
--soft-cream
--soft-sage
--bold-accent
--bg-primary
--text-primary
--border-primary
```

Why this matters:

The system supports multiple product moods: a warm customer app, a softer owner dashboard, and sharper operational staff screens.

### Typography

Fonts:

| Font | Use |
| --- | --- |
| `DM Sans` | Main UI body font |
| `Playfair Display` | Display headings and brand personality |
| `Cairo` / `Noto Sans Arabic` | Arabic and RTL text support |
| `JetBrains Mono` | Order numbers, IDs, compact technical labels |

Why this matters:

Restaurant apps need readable operational text, but Tablii also needs enough personality to feel like a polished hospitality product.

### Component Classes

Defined in:

```text
app/static/css/input.css
```

Important classes:

| Class | Purpose |
| --- | --- |
| `.btn-primary` | Main dark/amber action button |
| `.btn-secondary` | Secondary action |
| `.btn-danger` | Destructive action |
| `.input-field` | Standard dark form input |
| `.card`, `.card-hover` | General card surfaces |
| `.badge-*` | Order status badges |
| `.customer-app` | Mobile customer shell |
| `.customer-header` | Sticky customer header |
| `.customer-card` | Customer item/content card |
| `.customer-btn-primary` | Customer primary CTA |
| `.customer-bottom-panel` | Fixed mobile bottom action bar |
| `.customer-category-tab` | Horizontal menu category tab |

Why this matters:

Component classes reduce repeated Tailwind strings for common interface pieces and make the customer app easier to maintain.

## JavaScript Modules

| File | Responsibility |
| --- | --- |
| `app.js` | Global UI helpers |
| `cart.js` | Customer cart stored in `localStorage` |
| `socket.js` | Shared Socket.IO client setup and room helpers |
| `notifications.js` | Dashboard/staff notification behavior |
| `order_tracking.js` | Customer order status updates |
| `cashier_board.js` | Cashier order board interactions |
| `kitchen_display.js` | Kitchen display timers and status updates |
| `waiter_calls.js` | Waiter call notifications and resolve actions |
| `menu_builder.js` | Menu management interactions |
| `floor_map.js` | Table layout/floor map behavior |
| `analytics_charts.js` | Chart.js rendering helpers |

## Key Frontend Algorithms

### Customer Cart

File:

```text
app/static/js/cart.js
```

Workflow:

```text
1. Create a cart key from restaurant slug and table id.
2. Load existing cart from localStorage.
3. Add, remove, or update item quantities.
4. Calculate subtotal, tax, service charge, and total for display.
5. Save the cart back to localStorage.
6. Clear the cart after successful order placement.
```

Why this matters:

The cart should survive refreshes but stay isolated per restaurant and table. The backend still recalculates final prices, so frontend totals are for user feedback only.

### Socket Connection

File:

```text
app/static/js/socket.js
```

Workflow:

```text
1. Lazily create one Socket.IO connection.
2. Join a role-specific room.
3. Register handlers for events.
4. Play optional notification sounds.
```

Why this matters:

Lazy setup avoids unnecessary connections on pages that do not need realtime behavior. Role rooms keep each screen focused.

### Service Worker Cache Strategy

File:

```text
app/static/sw.js
```

Workflow:

```text
1. Cache selected static assets during install.
2. Delete old caches during activate.
3. Ignore non-GET and cross-origin requests.
4. Never cache dynamic Flask routes.
5. Use cache-first only for static assets.
```

Why this matters:

Static assets benefit from caching, but orders, dashboards, customer sessions, and staff screens must stay fresh. The service worker protects dynamic data by avoiding route caching.

### Analytics Charts

File:

```text
app/static/js/analytics_charts.js
```

Workflow:

```text
1. Receive JSON-serializable analytics data from the rendered page.
2. Create Chart.js instances for revenue, top items, peak hours, and statuses.
3. Destroy any existing chart instance before re-rendering.
4. Render chart-specific colors and labels.
```

Why this matters:

Chart.js gives readable analytics without building a chart engine from scratch.

## Frontend To Backend Contracts

### Server-rendered data

Most pages receive Python objects directly from Flask route handlers and render them through Jinja.

Examples:

- `restaurant`
- `table`
- `categories`
- `orders`
- `staff`
- `subscription`
- `analytics`

Why this matters:

Server rendering keeps the frontend simple and avoids needing a separate API call for every page load.

### JSON actions

Frontend scripts use `fetch()` for quick actions:

| Frontend action | Backend route |
| --- | --- |
| Toggle menu item | `POST /dashboard/menu/item/<id>/toggle` |
| Reorder menu/categories | Dashboard reorder routes |
| Place customer order | `POST /r/<slug>/table/<table_id>/order` |
| Call waiter | `POST /r/<slug>/table/<table_id>/call-waiter` |
| Update cashier order status | `POST /cashier/orders/<id>/status` |
| Mark kitchen order preparing/ready | `POST /kitchen/orders/<id>/<status>` |
| Mark waiter order served | `POST /waiter/orders/<id>/served` |
| Close table | `POST /waiter/tables/<table_id>/close` |
| Resolve waiter call | `POST /waiter/calls/<id>/resolve` |

Why this matters:

Small JSON/form actions make operational screens faster without turning the whole app into a SPA.

### CSRF

The base template exposes:

```html
<meta name="csrf-token" content="{{ csrf_token() }}" />
```

Why this matters:

JavaScript actions can include CSRF tokens for protected form routes. Customer JSON routes that are intentionally CSRF-exempt rely on table-session validation instead.

## Realtime Frontend Behavior

| Screen | Room joined | Main events |
| --- | --- | --- |
| Dashboard | `restaurant_<id>` | `new_notification`, order/table updates |
| Cashier | `cashier_<id>`, `restaurant_<id>` | `new_order`, `order_status_update` |
| Kitchen | `kitchen_<id>`, `restaurant_<id>` | `kitchen_new_order`, `order_status_update` |
| Waiter | `waiter_<staff_id>`, `restaurant_<id>` | `waiter_call`, `order_ready`, table updates |
| Customer tracking | `customer_<session_token>` | `order_status_update` |

Why this matters:

Realtime events are central to the product. Staff should not refresh pages to see new orders or calls.

## PWA Support

Files:

```text
app/static/manifest.json
app/static/sw.js
app/static/icons/icon-192.png
app/static/icons/icon-512.png
```

Current behavior:

- App can be installed as a standalone web app.
- Static CSS, JS, icons, logo, and default images are cached.
- Dynamic routes are network-only.
- Theme colors and icons are configured for mobile install prompts.

Why this matters:

Restaurants may use tablets or phones as operational devices. PWA support makes Tablii feel closer to a native app while keeping deployment simple.

## Responsive Design

The frontend uses responsive Tailwind utilities and mobile-first layout patterns.

Important patterns:

- Customer app is constrained to `max-w-lg` for mobile menu ergonomics.
- Bottom customer action panel respects `safe-area-inset-bottom`.
- Dashboard uses side navigation and dense content areas.
- Staff pages use large cards, high contrast, and touch-friendly buttons.
- Tables and lists often include alternate mobile card layouts.

Why this matters:

The same product is used on phones, tablets, laptops, and restaurant workstations. Each interface optimizes for the user's context.

## Accessibility Notes

Current strengths:

- Viewport meta tags are present.
- Buttons and links generally use clear visual focus states.
- Many operational actions have large touch targets.
- Status colors are paired with text labels.
- Arabic language support includes RTL direction in the global base.

Areas to keep improving:

- Ensure every icon-only button has an accessible label.
- Avoid relying on color alone for critical status.
- Keep table/list alternatives usable on small screens.
- Test customer checkout and staff boards with keyboard navigation.
- Confirm contrast after theme changes.

## Performance Notes

Current strengths:

- Tailwind CSS is compiled and minified.
- Vanilla JS avoids a heavy client framework bundle.
- Service worker caches static assets.
- Dynamic data is rendered server-side, reducing API waterfalls.

Risks:

- Socket.IO is loaded globally on some base templates even when not always needed.
- Google Fonts and CDN scripts add external network dependencies.
- Inline styles across templates make global redesigns harder.
- `output.css` should always be rebuilt after changing templates/classes.

## Build And Development

Install frontend dependencies:

```powershell
npm install
```

Build CSS:

```powershell
npm run build:css
```

Watch CSS during UI work:

```powershell
npm run watch:css
```

Tailwind scans:

```text
./app/templates/**/*.html
```

Why this matters:

If a class is only added dynamically in JavaScript, Tailwind may not include it unless it is safelisted or present in scanned templates.

## Frontend Quality Checklist

Before shipping frontend changes:

- Run `npm run build:css` after template or Tailwind class changes.
- Check mobile width for customer, waiter, and dashboard pages.
- Confirm forms show useful validation and flash messages.
- Confirm destructive actions use POST and clear labels.
- Confirm realtime events update the correct screen without refresh.
- Confirm staff actions include CSRF where required.
- Confirm active restaurant/location is visible in manager pages.
- Confirm Arabic/RTL pages do not break layout.
- Confirm dynamic text does not overflow buttons or cards.
- Confirm service worker is not caching dynamic restaurant/order routes.

## Recommended Improvements

| Priority | Recommendation | Reason |
| --- | --- | --- |
| High | Centralize more dashboard CSS variables/components | Reduces duplicated inline styles |
| High | Lazy-load Socket.IO only on realtime pages | Reduces unnecessary network and JS work |
| Medium | Add a small frontend convention guide for new templates | Keeps future pages visually consistent |
| Medium | Add accessibility checks for key flows | Protects customer ordering and staff operations |
| Medium | Safelist dynamic Tailwind classes used only in JS | Prevents missing styles after production builds |
| Low | Move repeated staff theme CSS into shared classes | Easier long-term maintenance |

## Conclusion

The Tablii frontend is a pragmatic Flask-rendered interface with targeted JavaScript for restaurant workflows. Its strongest design choice is separating interfaces by user context: customers get a mobile ordering app, staff get realtime workstations, managers get an operational dashboard, and admins get a platform control panel.

The next frontend maturity step is not a framework rewrite. The best improvement is to continue extracting repeated CSS and interaction patterns into shared components while preserving the current fast, server-rendered workflow.
