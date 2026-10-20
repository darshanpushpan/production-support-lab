# Observability plan: Prometheus + Grafana

Status: plan. None of this is built yet. Next step after this doc is adding it to docker-compose.

The goal is simple. Every SLO in [slos.md](slos.md) needs a metric behind it and a panel on a dashboard. If I can't measure an SLO, it's just a wish.

## How the pieces connect

```
api     /metrics  (port 8000) ┐
worker  /metrics  (port 9100) ┼──> Prometheus (scrapes every 15s) ──> Grafana dashboard
                              ┘
```

- Prometheus pulls metrics from each service. The services don't push anything.
- Grafana only reads from Prometheus. Datasource and dashboard are provisioned from files in the repo, so `docker compose up` gives the same dashboard every time instead of me clicking it together by hand.
- Prometheus and Grafana ports bound to 127.0.0.1, same as everything else.

## Metrics

| Metric | Type | From | Used for |
|---|---|---|---|
| `http_requests_total{handler, method, status}` | counter | api | SLO 1 availability |
| `http_request_duration_seconds{handler, method}` | histogram | api | SLO 2 latency |
| `order_processing_seconds` | histogram | worker | SLO 3 processing time (processed_at minus created_at) |
| `orders_pending` | gauge | worker | how many orders are waiting right now |
| `orders_oldest_pending_seconds` | gauge | worker | SLO 4 lost orders (anything pending over 10 min) |

The worker has no web server, so it gets a tiny one just for `/metrics` on port 9100.

Histogram buckets need to include 0.5 for the API and 30 for the worker, otherwise I can't measure "under 500 ms" and "within 30 seconds" exactly.

## How each SLO is calculated (PromQL)

1. Availability: requests that weren't 5xx, divided by all requests
   `sum(rate(http_requests_total{handler="/orders", status!~"5.."}[7d])) / sum(rate(http_requests_total{handler="/orders"}[7d]))`
2. Latency: POST /orders requests under 0.5s, divided by all POST /orders requests
   `sum(rate(http_request_duration_seconds_bucket{handler="/orders", method="POST", le="0.5"}[7d])) / sum(rate(http_request_duration_seconds_count{handler="/orders", method="POST"}[7d]))`
3. Processing time: orders done within 30s, divided by all processed orders
   `sum(rate(order_processing_seconds_bucket{le="30.0"}[7d])) / sum(rate(order_processing_seconds_count[7d]))`
4. Lost orders: oldest pending order in seconds, should stay under 600
   `orders_oldest_pending_seconds`

## Dashboard (one page)

Top row: one stat panel per SLO, current value vs target, green or red.
Second row: request rate and error rate, latency over time, orders pending, oldest pending order.

## Decisions

- **Plain Prometheus client libraries, not OpenTelemetry, for now.** OpenTelemetry is more flexible but adds a collector and more config. For 2 services, the client libraries are less to learn and less to break. I can switch later if I add tracing.
- **The worker reports the queue, not a separate exporter.** It already queries pending orders, so counting them there is one query, not another container.
- **The stopped-worker test should show up on the dashboard.** If the worker is dead, it can't report metrics, so Prometheus will mark that target as down. That's a second signal on top of `orders_pending` going up. I need to make sure the dashboard shows both.

## What I still won't see after this

- Logs. Loki comes later.
- Anything about Postgres itself (connections, slow queries).
- Why something is slow. Metrics will say that latency went up, not which part of the request caused it.
