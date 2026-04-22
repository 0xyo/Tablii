# Tablii Entity-Relationship Diagram

## Order Status Flow

```mermaid
stateDiagram-v2
    [*] --> new : Client places order
    new --> accepted : Cashier accepts
    accepted --> preparing : Kitchen starts
    preparing --> ready : Kitchen completes
    ready --> served : Waiter serves
    served --> completed : Payment confirmed
    new --> rejected : Cashier rejects
    rejected --> [*]
```

## Multi-Tenant Architecture

```mermaid
graph TB
    subgraph "Platform"
        SA["Super Admin"]
    end
    
    subgraph "Restaurant 1"
        R1["Restaurant"]
        OU1["Owner"]
        S1_1["Cashier"]
        S1_2["Kitchen"]
        S1_3["Waiter"]
    end
    
    subgraph "Restaurant 2"
        R2["Restaurant"]
        OU2["Owner"]
    end
    
    SA --> R1
    SA --> R2
    OU1 --> S1_1
    OU1 --> S1_2
    OU1 --> S1_3
```

## Database Schema (Simplified)

| Table | Description | Key Fields |
|-------|-------------|------------|
| users | Platform owners & admins | id, email, role |
| staff_users | Restaurant staff | id, restaurant_id, role |
| customers | End customers | id, phone |
| restaurants | Restaurant tenants | id, owner_id, slug |
| categories | Menu categories | id, restaurant_id |
| menu_items | Menu items | id, category_id, price |
| customizations | Item options | id, menu_item_id |
| tables_ | Restaurant tables | id, restaurant_id |
| table_sessions | Active sessions | id, table_id |
| orders | Customer orders | id, session_id, status |
| order_items | Order line items | id, order_id, menu_item_id |
| payment_transactions | Flouci payments | id, order_id |
| waiter_calls | Customer requests | id, table_id |
| reviews | Order reviews | id, order_id |
| loyalty_points | Customer loyalty | id, customer_id, restaurant_id |
| notifications | Staff alerts | id, restaurant_id |
| subscriptions | Restaurant plans | id, restaurant_id |
| operating_hours | Weekly schedule | id, restaurant_id |

## Key Features Mapping

| Feature | Implementation |
|--------|---------------|
| Multi-tenant | `restaurant_id` FK on tenant tables |
| Multi-language | `name_fr`, `name_ar`, `name_en` fields |
| Real-time | WebSocket (Flask-SocketIO) |
| Payment | `payment_transactions` table |
| Loyalty | `loyalty_points` table |
| Ramadan | `ramadan_mode` + `ramadan_type` |
| Gift orders | `is_gift`, `gift_from_table` |
| QR codes | `qr_code_url` in `tables_` |
| Subscriptions | `subscriptions` table |
| Operating hours | `operating_hours` table |
