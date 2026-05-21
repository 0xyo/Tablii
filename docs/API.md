# API Reference

This document covers the JSON API, customer table endpoints, realtime Socket.IO events, and important HTML form routes exposed by the Tablii backend.

## Base URL

Local development:

```text
http://127.0.0.1:5000
```

Production:

```text
https://your-domain.example
```

All examples use the local base URL.

## Response Conventions

JSON endpoints return JSON objects. Errors usually use one of these shapes:

```json
{ "error": "Message" }
```

or:

```json
{ "success": false, "error": "Message" }
```

Successful customer actions usually include:

```json
{ "success": true }
```

## Authentication And CSRF

| Endpoint group | Authentication | CSRF |
| --- | --- | --- |
| `/api/restaurant/...` | Public | Exempt |
| `/api/menu-item/...` | Public | Exempt |
| `/api/order/.../status` | Public by order ID | Exempt |
| `/api/upload-image` | Requires Flask-Login session | Exempt blueprint, but login required |
| `/r/<slug>/table/...` JSON endpoints | Browser table session | Selected routes exempt |
| Dashboard/staff/admin form routes | Login required | CSRF protected unless explicitly exempt |

The customer ordering flow relies on the Flask browser session. The first visit to the QR menu route creates or reuses a `TableSession` and stores `session_token` in the browser session.

## Public JSON API

### Get Restaurant Menu

Returns the active menu for a restaurant.

```http
GET /api/restaurant/<slug>/menu
```

Query parameters:

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `lang` | string | No | `fr`, `ar`, or `en`. Defaults to restaurant default language, then `fr`. |

Example:

```powershell
curl "http://127.0.0.1:5000/api/restaurant/chez-ahmed/menu?lang=fr"
```

Success response:

```json
{
  "restaurant": {
    "name": "Chez Ahmed",
    "slug": "chez-ahmed",
    "currency": "TND",
    "description": "Traditional restaurant"
  },
  "categories": [
    {
      "id": 1,
      "name": "Plats",
      "icon": "utensils",
      "items": [
        {
          "id": 10,
          "name": "Couscous",
          "description": "Couscous maison",
          "price": 18.5,
          "image_url": "/static/uploads/menu/couscous.jpg",
          "is_available": true,
          "is_popular": false,
          "prep_time": 20,
          "customizations": [
            {
              "id": 3,
              "group_name": "Sauce",
              "type": "single",
              "required": false,
              "options": [
                {
                  "id": 7,
                  "name": "Harissa",
                  "extra_price": 0.0,
                  "is_default": false
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

Errors:

| Status | Response |
| --- | --- |
| `404` | `{ "error": "Restaurant not found" }` |

### Get Menu Item

Returns one menu item with its customization groups.

```http
GET /api/menu-item/<item_id>
```

Query parameters:

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `restaurant_id` | integer | No | Scopes lookup to one restaurant/location. Recommended. |
| `lang` | string | No | `fr`, `ar`, or `en`. Defaults to `fr`. |

Example:

```powershell
curl "http://127.0.0.1:5000/api/menu-item/10?restaurant_id=1&lang=en"
```

Success response:

```json
{
  "id": 10,
  "name": "Couscous",
  "price": 18.5,
  "description": "House couscous",
  "image_url": "/static/uploads/menu/couscous.jpg",
  "is_available": true,
  "is_popular": false,
  "restaurant_id": 1,
  "customizations": []
}
```

Errors:

| Status | Response |
| --- | --- |
| `404` | `{ "error": "Item not found" }` |

### Get Order Status

Returns status and timestamps for an order.

```http
GET /api/order/<order_id>/status
```

Example:

```powershell
curl "http://127.0.0.1:5000/api/order/25/status"
```

Success response:

```json
{
  "order_id": 25,
  "order_number": "A104",
  "status": "preparing",
  "payment_status": "pending",
  "timestamps": {
    "created_at": "2026-05-21T12:00:00",
    "accepted_at": "2026-05-21T12:01:00",
    "preparing_at": "2026-05-21T12:04:00",
    "ready_at": null,
    "served_at": null,
    "completed_at": null
  }
}
```

Errors:

| Status | Response |
| --- | --- |
| `404` | `{ "error": "Order not found" }` |

### Upload Image

Uploads an image and returns the public URL.

```http
POST /api/upload-image
```

Authentication:

- Requires a logged-in Flask session.

Request:

| Field | Type | Required |
| --- | --- | --- |
| `file` | multipart file | Yes |

Example:

```powershell
curl -X POST "http://127.0.0.1:5000/api/upload-image" -F "file=@C:\path\image.jpg"
```

Success response:

```json
{
  "url": "/static/uploads/api/image.jpg"
}
```

Errors:

| Status | Response |
| --- | --- |
| `400` | `{ "error": "No file provided" }` |
| `400` | `{ "error": "Invalid or unsupported file" }` |
| `401` | Login required |

## Customer Table JSON Endpoints

Customer endpoints are scoped by restaurant slug and table ID:

```text
/r/<slug>/table/<table_id>
```

The first page visit to `GET /r/<slug>/table/<table_id>` creates or reuses the active table session. JSON order actions require that browser session.

### Identify Customer

Links a guest name and optional phone number to the current table session.

```http
POST /r/<slug>/table/<table_id>/identify
```

Request:

```json
{
  "name": "Mira",
  "phone": "+21620000000"
}
```

Success:

```json
{
  "success": true,
  "name": "Mira"
}
```

Errors:

| Status | Meaning |
| --- | --- |
| `400` | Name is missing |
| `403` | No active session or session expired |

### Place Order

Creates a new order from the table cart.

```http
POST /r/<slug>/table/<table_id>/order
```

Request:

```json
{
  "items": [
    {
      "menu_item_id": 10,
      "quantity": 2,
      "selected_options": [7, 8],
      "notes": "No onion"
    }
  ],
  "payment_method": "cash",
  "special_notes": "Bring bread first",
  "is_gift": false
}
```

Gift order request:

```json
{
  "items": [
    {
      "menu_item_id": 10,
      "quantity": 1,
      "selected_options": []
    }
  ],
  "payment_method": "cash",
  "is_gift": true,
  "gift_to_table": 4,
  "gift_message": "Enjoy!"
}
```

Success:

```json
{
  "success": true,
  "order_id": 25,
  "order_number": "A104",
  "total_amount": 42.5
}
```

Validation:

- Restaurant must be open.
- Browser must have an active table session.
- Order must contain at least one item.
- Quantity must be an integer from 1 to 20.
- Menu items must belong to the same restaurant and be available.
- Customization max selections are enforced.
- Gift target table must be occupied and cannot be the current table.
- Expired subscriptions block order creation.

Errors:

| Status | Meaning |
| --- | --- |
| `400` | Invalid cart, item, quantity, customization, or gift table |
| `403` | Restaurant closed, invalid session, or expired session |
| `500` | Unexpected server error |

### Get Occupied Tables

Returns occupied tables in the same restaurant, excluding the current table. Used by gift ordering.

```http
GET /r/<slug>/table/<table_id>/occupied-tables
```

Success:

```json
{
  "tables": [
    {
      "id": 4,
      "table_number": "12"
    }
  ]
}
```

### Call Waiter

Creates a waiter call.

```http
POST /r/<slug>/table/<table_id>/call-waiter
```

Request:

```json
{
  "call_type": "water",
  "message": ""
}
```

Allowed `call_type` values:

| Value | Meaning |
| --- | --- |
| `water` | Customer asks for water |
| `bill` | Customer asks for bill |
| `help` | Customer asks for help |
| `custom` | Customer sends a custom message |

For `custom`, `message` is required.

Success:

```json
{
  "success": true
}
```

Errors:

| Status | Meaning |
| --- | --- |
| `400` | Invalid call type or missing custom message |
| `500` | Unexpected server error |

## Customer HTML Routes

These routes render pages and are useful for frontend integration.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/r/<slug>/table/<table_id>` | QR menu page |
| `GET` | `/r/<slug>/table/<table_id>/cart` | Cart page |
| `GET` | `/r/<slug>/table/<table_id>/checkout` | Checkout page |
| `GET` | `/r/<slug>/table/<table_id>/track/<order_id>` | Order tracking page |
| `GET` | `/r/<slug>/table/<table_id>/call-waiter` | Call waiter page |
| `GET` | `/r/<slug>/table/<table_id>/review/<order_id>` | Review form |
| `POST` | `/r/<slug>/table/<table_id>/review/<order_id>` | Submit review |
| `GET` | `/r/<slug>/table/<table_id>/order/<order_id>/pay` | Start Flouci payment |
| `GET` | `/r/<slug>/table/<table_id>/order/<order_id>/payment/callback` | Flouci callback |

## Manager Dashboard Routes

Dashboard routes are server-rendered and require an authenticated owner account. Most routes use `restaurant_required` and act on the active location.

### Locations

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/dashboard/locations` | List owned locations, current active location, and usage |
| `POST` | `/dashboard/locations/add` | Create a new location if under `max_locations` |
| `POST` | `/dashboard/locations/<id>/switch` | Store selected location in the session |
| `POST` | `/dashboard/locations/<id>/archive` | Archive a location by setting `Restaurant.is_active = False` |

### Menu

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/dashboard/menu/categories` | Manage categories |
| `POST` | `/dashboard/menu/categories/add` | Add category |
| `POST` | `/dashboard/menu/categories/<id>/update` | Update category |
| `POST` | `/dashboard/menu/categories/<id>/delete` | Delete category |
| `POST` | `/dashboard/menu/categories/reorder` | Reorder categories |
| `GET` | `/dashboard/menu/items` | Manage items |
| `GET`, `POST` | `/dashboard/menu/item/new` | Create menu item |
| `GET`, `POST` | `/dashboard/menu/item/<id>/edit` | Edit menu item |
| `POST` | `/dashboard/menu/item/<id>/delete` | Delete menu item |
| `POST` | `/dashboard/menu/item/<id>/toggle` | Toggle item availability |
| `POST` | `/dashboard/menu/items/reorder` | Reorder items |
| `GET` | `/dashboard/menu/item/<item_id>/customizations` | Manage item customizations |
| `POST` | `/dashboard/menu/item/<item_id>/customizations/add` | Add customization group |
| `POST` | `/dashboard/menu/customizations/<id>/options/add` | Add customization option |
| `POST` | `/dashboard/menu/customizations/<id>/delete` | Delete customization |

### Tables, Staff, Orders, Settings

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/dashboard/tables` | Manage tables |
| `POST` | `/dashboard/tables/add` | Add table, limited by plan |
| `POST` | `/dashboard/tables/layout` | Save table layout |
| `POST` | `/dashboard/tables/<id>/delete` | Delete table |
| `GET` | `/dashboard/tables/<id>/qr` | Download/display QR code |
| `POST` | `/dashboard/tables/<id>/assign-waiter` | Assign waiter to table |
| `GET` | `/dashboard/staff` | List staff |
| `GET`, `POST` | `/dashboard/staff/add` | Create staff user |
| `GET`, `POST` | `/dashboard/staff/<id>/edit` | Edit staff user |
| `POST` | `/dashboard/staff/<id>/delete` | Delete staff user |
| `GET` | `/dashboard/orders/history` | Order history |
| `GET`, `POST` | `/dashboard/settings` | Restaurant settings |
| `GET` | `/dashboard/analytics` | Analytics |
| `GET` | `/dashboard/reviews` | Reviews |
| `GET` | `/dashboard/notifications` | Notifications |
| `GET` | `/dashboard/notifications/count` | Notification count JSON |
| `POST` | `/dashboard/notifications/<notification_id>/read` | Mark one notification read |
| `POST` | `/dashboard/notifications/read-all` | Mark all notifications read |
| `GET` | `/dashboard/subscription` | Subscription page |
| `POST` | `/dashboard/subscription/change` | Change plan |

## Staff Routes

Staff users are scoped to one `restaurant_id`.

### Cashier

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/cashier/profile` | Cashier profile |
| `GET` | `/cashier/orders` | Cashier order board |
| `POST` | `/cashier/orders/<id>/status` | Move order status |
| `GET`, `POST` | `/cashier/manual-order` | Create manual order |
| `POST` | `/cashier/orders/<id>/confirm-payment` | Mark order paid |

### Kitchen

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/kitchen/profile` | Kitchen profile |
| `GET` | `/kitchen` | Kitchen display |
| `POST` | `/kitchen/orders/<id>/preparing` | Mark order preparing |
| `POST` | `/kitchen/orders/<id>/ready` | Mark order ready |

### Waiter

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/waiter/profile` | Waiter profile |
| `GET` | `/waiter/tables` | Assigned/restaurant tables |
| `GET` | `/waiter/calls` | Waiter calls |
| `POST` | `/waiter/calls/<id>/resolve` | Resolve call |
| `POST` | `/waiter/orders/<id>/served` | Mark order served |
| `POST` | `/waiter/tables/<table_id>/close` | Close table session |
| `POST` | `/waiter/orders/<id>/confirm-payment` | Mark order paid |

## Admin Routes

Super admin routes require `super_admin_required`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/admin/profile` | Super admin profile |
| `GET` | `/admin/restaurants` | List restaurants |
| `POST` | `/admin/restaurants/<restaurant_id>/toggle` | Activate/deactivate restaurant |
| `GET` | `/admin/subscriptions` | Manage subscriptions |
| `POST` | `/admin/subscriptions/<sub_id>/update` | Update plan, limits, expiry, payment state |
| `GET` | `/admin/analytics` | Platform analytics |

## Socket.IO API

### Client Join Events

Clients should join the room matching their role after connecting.

```javascript
socket.emit("join_restaurant", { restaurant_id: 1 });
socket.emit("join_cashier", { restaurant_id: 1 });
socket.emit("join_kitchen", { restaurant_id: 1 });
socket.emit("join_waiter", { restaurant_id: 1, waiter_id: 4 });
socket.emit("join_customer", { session_token: "session-token" });
```

### Server Events

| Event | Payload highlights | Sent when |
| --- | --- | --- |
| `new_order` | `order_id`, `order_number`, `table_number`, `items`, `total_amount`, `status` | A customer or cashier creates an order |
| `new_notification` | `type` | A new lightweight notification is available |
| `kitchen_new_order` | Order and item details | An order is accepted and sent to kitchen |
| `order_status_update` | `order_id`, `status`, timestamps | An order changes status |
| `order_ready` | `order_id`, `table_number` | Kitchen marks order ready |
| `waiter_call` | `call_id`, `table_number`, `call_type`, `message` | Customer calls waiter |
| `table_status_change` | Table details and status | Table is freed or status changes |

## Order And Payment Status Values

Order statuses:

```text
new
accepted
preparing
ready
served
completed
cancelled
```

Payment statuses:

```text
pending
paid
failed
refunded
```

Payment methods commonly used:

```text
cash
online
```

## Versioning Notes

The current API is unversioned. For external clients, prefer treating paths and response fields as stable but additive. If a breaking change is needed later, add a version prefix such as:

```text
/api/v1/...
```
