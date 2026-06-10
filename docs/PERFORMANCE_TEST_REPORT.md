# Performance Test Report

## 1. Objective

The objective of this performance test was to evaluate the stability,
responsiveness, and saturation behavior of Tablii under simulated restaurant
traffic. The test focused on customer-facing flows because they are the most
traffic-sensitive part of the system: browsing the QR menu, identifying a
customer, creating orders, polling order status, and calling a waiter.

## 2. Test Environment

| Item | Configuration |
| --- | --- |
| Application | Tablii restaurant ordering platform |
| Backend | Flask, Flask-SocketIO, SQLAlchemy |
| Test tool | k6 with Grafana Cloud result streaming |
| Execution mode | Local k6 execution |
| Result dashboard | Grafana Cloud k6 |
| Target base URL | `http://127.0.0.1:5000` |
| Dataset | Seeded demo restaurant: `chez-ahmed` |
| Database | Local development database |
| Test date | 2026-06-10 |

The tests were executed from the same local machine as the application. This is
useful for development validation, but it is not a final production capacity
measurement because the local Flask server, local database, and laptop resources
can become the bottleneck.

## 3. Workloads

The k6 script is located at `scripts/k6/restaurant-flow.js`.

### Read-Only Smoke Workload

This workload validates availability and baseline response time without writing
to the database.

Main operations:

- Fetch public restaurant menu.
- Fetch menu item details.
- Render customer QR menu and cart pages.

### Mixed Load Workload

This workload simulates a realistic restaurant session and creates database
records.

Main operations:

- Browse menu.
- Open customer table session.
- Identify customer.
- Create orders.
- Poll order status.
- Create waiter calls.

## 4. Test Commands

Smoke test:

```powershell
npm run smoke:cloud
```

Load test:

```powershell
npm run load:cloud
```

Stress test:

```powershell
npm run stress:cloud
```

Targeted stress test:

```powershell
k6 run -o cloud -e MODE=stress -e STRESS_STAGES=25:1m,40:1m,60:1m,80:1m scripts/k6/restaurant-flow.js
```

## 5. Results Summary

| Test | Max VUs | Workload | Requests | Orders | Failure Rate | Avg Latency | p95 Latency | p99 Latency | Throughput |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Smoke | 5 | Read-only | 421 | 0 | 0.00% | 7.20 ms | 13.17 ms | 23.29 ms | 15.01 req/s |
| Load | 25 | Mixed | 4,765 | 589 | 0.00% | 179.39 ms | 462.91 ms | 663.17 ms | 55.57 req/s |
| Stress | 100 | Mixed | 8,775 | 1,138 | 0.00% | 490.20 ms | 1.63 s | 2.75 s | 52.03 req/s |
| Targeted Stress | 80 | Mixed | 12,888 | 1,663 | 0.00% | 563.12 ms | 1.48 s | 2.38 s | 52.99 req/s |

## 6. Findings

The application remained functionally stable across all executed tests. No HTTP
request failures were observed, and all generated order requests succeeded.

At 25 virtual users, the system showed healthy behavior for a local development
environment. The p95 latency remained under 500 ms, and throughput reached
approximately 55 requests per second.

At 80 virtual users, the system still passed the configured 1.5 second p95
latency threshold, with 0% request failures and 0% order creation failures.
However, the p95 latency reached 1.48 seconds, which is close to the configured
limit.

At 100 virtual users, the application continued to avoid errors, but p95 latency
increased to 1.63 seconds and exceeded the performance threshold. Throughput did
not increase compared with the 25 and 80 VU tests, remaining around 52 to 55
requests per second. This indicates saturation: adding more virtual users
increased waiting time instead of increasing completed work.

## 7. Capacity Interpretation

Based on the local tests, Tablii can be considered stable up to approximately
80 concurrent virtual users for the tested mixed customer workload. The practical
comfort zone is closer to 25 to 60 virtual users, where latency remains clearly
below the threshold.

The saturation point appears to begin between 80 and 100 virtual users. At that
level, the application remains available and correct, but user experience starts
to degrade because response times become noticeably higher.

## 8. Limitations

These results should not be treated as final production capacity numbers.

Main limitations:

- Tests were executed against a local development server.
- Local database behavior may differ from PostgreSQL in production.
- k6 and the application ran from the same machine, so they shared CPU, memory,
  disk, and network resources.
- The test focused mostly on customer-facing flows, not owner dashboard, kitchen
  display, cashier workflow, or WebSocket-heavy staff sessions.
- The test data was demo seed data, not a large production-sized database.

## 9. Recommended Improvements

For the current academic/project context, the results are strong enough to
document that the system is stable under meaningful local load.

For a more professional production benchmark, the next improvements are:

- Run the application behind Gunicorn instead of the Flask development server.
- Test against PostgreSQL instead of the local development database.
- Deploy a staging environment that matches production more closely.
- Add endpoint-level Grafana analysis to identify the slowest route under load.
- Add database query profiling for order creation and menu loading.
- Add indexes where repeated query patterns show high latency.
- Separate static asset serving from Flask in production.
- Test staff real-time workflows, especially kitchen and cashier screens using
  Socket.IO.

## 10. Conclusion

The performance test demonstrates that Tablii handles realistic customer traffic
reliably in the local test environment. The system processed thousands of
requests and more than one thousand order creations without request failures or
order creation failures.

The best observed operating range is up to approximately 80 virtual users under
the tested workload. Beyond that point, throughput stops increasing and latency
crosses the target threshold, indicating that production optimization should
focus on the web server, database, and write-heavy order creation path.
