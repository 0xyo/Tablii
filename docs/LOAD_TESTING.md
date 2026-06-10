# Load And Stress Testing

Tablii includes a k6 scenario script at `scripts/k6/restaurant-flow.js`. It
simulates browser-like restaurant traffic with a separate cookie jar per virtual
user, so customer table sessions behave like the QR menu flow.

For the latest analyzed test results, see
[`PERFORMANCE_TEST_REPORT.md`](./PERFORMANCE_TEST_REPORT.md).

## What It Exercises

- Public menu API: `GET /api/restaurant/<slug>/menu`
- Menu item details: `GET /api/menu-item/<item_id>`
- Customer QR menu pages: `GET /r/<slug>/table/<table_id>`
- Customer identification: `POST /identify`
- Order creation: `POST /order`
- Order status polling: `GET /api/order/<order_id>/status`
- Waiter calls: `POST /call-waiter`

The default `mixed` workload creates real local orders and waiter calls. Use
`WORKLOAD=read` for a read-only smoke test.

## Prepare The Local App

From the project root:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask db upgrade
python seed.py
python run.py
```

Leave the Flask server running at `http://127.0.0.1:5000`. Open a second
terminal for k6.

## Quick Smoke Test

```powershell
k6 run -e WORKLOAD=read -e VUS=5 -e DURATION=15s -e RAMP_UP=3s scripts/k6/restaurant-flow.js
```

This confirms the app is reachable and that menu endpoints respond before you
create test orders.

## Send Results To Grafana Cloud

For local development, run k6 on your machine and stream the results to Grafana
Cloud:

```powershell
k6 cloud login --stack cosmicbroccoli1441
k6 run -o cloud -e WORKLOAD=read -e VUS=5 -e DURATION=15s -e RAMP_UP=3s scripts/k6/restaurant-flow.js
```

Or use the npm shortcut:

```powershell
npm run smoke:cloud
```

This is the right mode when `BASE_URL` is `http://127.0.0.1:5000`, because your
local machine can reach the Flask app and Grafana Cloud receives the metrics.

To run the load generators inside Grafana Cloud instead, the app must be on a
public URL:

```powershell
k6 cloud run -e BASE_URL=https://your-public-app.example -e WORKLOAD=read scripts/k6/restaurant-flow.js
```

For `WORKLOAD=mixed` or `WORKLOAD=orders` against a public staging app, add
`-e ALLOW_NON_LOCAL_WRITES=1` because those modes create test orders.

## Load Test

Use this for a steady expected traffic level:

```powershell
k6 run -e MODE=load -e WORKLOAD=mixed -e VUS=25 -e DURATION=1m -e RAMP_UP=15s scripts/k6/restaurant-flow.js
```

k6 reports request rate, failure rate, latency percentiles, thresholds, and the
custom `orders_created`, `waiter_calls_created`, and `place_order_failures`
metrics.

## Stress Test

Use this to find where the app starts failing or latency becomes unacceptable:

```powershell
k6 run -e MODE=stress -e STRESS_STAGES=10:30s,25:45s,50:45s,100:45s scripts/k6/restaurant-flow.js
```

Each entry in `STRESS_STAGES` is `target_vus:duration`. The first stage where
failure rate or p95 latency climbs sharply is your likely breaking point.

## Useful Environment Variables

- `BASE_URL=http://127.0.0.1:5000`: target host.
- `SLUG=chez-ahmed`: restaurant slug.
- `TABLES=1-8`: table IDs to use; comma lists and ranges are supported.
- `WORKLOAD=read`: read-only menu/page traffic.
- `WORKLOAD=mixed`: menu traffic plus orders and waiter calls.
- `WORKLOAD=orders`: mostly order creation.
- `MODE=load`: ramp to `VUS`, hold for `DURATION`, then ramp down.
- `MODE=stress`: use `STRESS_STAGES`.
- `VUS=50`: concurrent virtual users for load mode.
- `DURATION=2m`: steady load duration.
- `RAMP_UP=30s`: gradual startup for load mode.
- `FAIL_RATE=0.05`: failure-rate threshold.
- `P95_MS=1500`: p95 latency threshold in milliseconds.

## Safety Notes

- `mixed` and `orders` create database rows. Prefer a seeded local database or a
  disposable staging database.
- The script refuses to create orders against non-local hosts unless you set
  `ALLOW_NON_LOCAL_WRITES=1`.
- Do not run stress tests against production without permission, a maintenance
  window, monitoring, and a cleanup plan.
- The Flask development server and SQLite are useful for local feedback, but
  production capacity should be tested against the same web server, database,
  and hosting shape you deploy.

## Interpreting Results

For a healthy load-test stage, aim for:

- Failure rate near `0%`.
- Stable p95 latency as virtual users increase.
- No single endpoint dominating failures.
- `POST /order` staying within your acceptable p95 latency target.

Stress testing is allowed to fail. The useful result is the point where errors,
timeouts, or p95/p99 latency start climbing faster than the user count.
