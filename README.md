# 🏗️ TABLII — Phase-by-Phase Implementation Guide

> **12 professional AI prompts** to build the Tablii restaurant management platform from scratch. Each phase builds on the previous one. Execute them **in order**.

---

## Phase Overview

| #   | Phase                                                    | Key Deliverables                                      |
| --- | -------------------------------------------------------- | ----------------------------------------------------- |
| 01  | [Project Foundation](phase-01-project-foundation.md)     | Flask factory, config, requirements, Tailwind setup   |
| 02  | [Database Models](phase-02-database-models.md)           | 15+ SQLAlchemy models, migrations                     |
| 03  | [Core Utilities](phase-03-core-utilities.md)             | Decorators, validators, helpers, QR & upload services |
| 04  | [Authentication](phase-04-authentication.md)             | Owner/staff login, register, base template, CSS       |
| 05  | [Customer Interface](phase-05-customer-interface.md)     | Menu, cart, checkout, order tracking, reviews         |
| 06  | [Dashboard Management](phase-06-dashboard-management.md) | Menu CRUD, tables, staff, settings, order history     |
| 07  | [Staff Interfaces](phase-07-staff-interfaces.md)         | Cashier board, kitchen display, waiter view           |
| 08  | [WebSocket Real-Time](phase-08-websocket-realtime.md)    | SocketIO events, rooms, live notifications            |
| 09  | [Payments & Analytics](phase-09-payments-analytics.md)   | Flouci gateway, analytics charts, notifications       |
| 10  | [Frontend & PWA](phase-10-frontend-pwa.md)               | PWA, service worker, remaining JS, CSS polish         |
| 11  | [API, Admin & Testing](phase-11-api-admin-testing.md)    | JSON API, super admin, pytest, seed data              |
| 12  | [Deployment & Docs](phase-12-deployment-docs.md)         | Render.com config, documentation, launch checklist    |

---

## How to Use

1. **Feed each phase file as a prompt** to an AI coding assistant.
2. **Wait for the phase to be fully implemented and validated** before moving to the next.
3. Each phase has a **Validation Checklist** — verify all items pass before proceeding.
4. Each phase has **Strict Rules** — these prevent hallucination and scope creep.

---

## Tech Stack

- **Backend**: Python 3.11, Flask 3.0, SQLAlchemy 2.0, Flask-SocketIO
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Jinja2 templates, Tailwind CSS 3.4, Vanilla JavaScript
- **Real-time**: Flask-SocketIO with eventlet
- **Payments**: Flouci (Tunisian gateway)
- **Deployment**: Render.com (free tier)
