# Title: Prometheus and Grafana running, and the dead worker test on a dashboard
Date: 2026-10-19

## What I did
Built the observability plan from last week.
- API: counts every request by route, method and status, and records request time in a histogram with a 0.5s bucket. Exposed on /metrics.
- Worker: records how long each order took from created to processed (histogram with a 30s bucket), how many orders are pending, and the age of the oldest pending order. The worker has no web server, so it serves /metrics on port 9100 just for Prometheus.
- Prometheus scrapes both every 15 seconds.
- Grafana dashboard is provisioned from a JSON file in the repo: one panel per SLO, api/worker UP or DOWN, pending orders, request rate by status, p95 latency.
- Added a load generator that sends about 30 fake orders a minute so the graphs have something on them.

## What broke or surprised me
1. The load generator's first order failed with "unreachable". depends_on only waits for the API container to start, not for uvicorn to be listening. Fixed by adding a healthcheck on the API and making loadgen wait for service_healthy.
2. The SLO 3 panel (processed within 30s) showed no data even though the worker had processed 28 orders. The query used le="30", but the bucket is stored as le="30.0". PromQL matches label values as exact text, so it matched nothing, and it didn't error. SLO 2 only worked because 0.5 is already written that way.
3. The dead worker test went exactly like the plan said. I stopped the worker and Prometheus marked it down about 20 seconds later (15s scrape interval). orders_pending went to no data instead of going up, because the worker is the one that reports it. Postgres had 14 orders pending at that point, oldest 23 seconds. So the "worker DOWN" panel is the thing that actually catches it.

## What I tried (including what didn't work)
le="30" first, then checked the real label values with /api/v1/series and switched to le="30.0".

## Decision and why
- Wrote my own small middleware for the API metrics instead of a library, so I control the metric names and buckets and they match the plan.
- Used the route template (/orders/{order_id}) as the handler label, not the real path, otherwise every order id would become its own time series.
- Grafana admin password comes from .env, sign up disabled, port on 127.0.0.1.

## Evidence
- devlog/evidence/2026-10-19-loadgen-unreachable.txt
- devlog/evidence/2026-10-19-le-label.txt
- devlog/evidence/2026-10-19-worker-down.txt
- observability/grafana/dashboards/slo-overview.json

## Update Oct 20, 00:44
I left the worker stopped after the test and took a Grafana screenshot about 4.5 hours later. Postgres had 3014 pending orders, the oldest 278 minutes old. The dashboard was green everywhere except the worker DOWN panel:
- SLO 3 still said 100%, because it only counts orders that finished. Orders stuck in the queue never get counted at all.
- SLO 4 and orders pending showed "no data" on a green background. No data shouldn't look healthy.

Things to fix: a no data state that isn't green, and an SLO 4 that doesn't depend on the worker being alive (query Postgres directly or alert on the worker being down).

Evidence: devlog/evidence/2026-10-20-worker-down-overnight.txt, devlog/screenshots/grafana-worker-down.png
