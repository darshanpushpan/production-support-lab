# Title: Planning how to measure the SLOs before adding Prometheus and Grafana
Date: 2026-10-13

## What I did
Wrote docs/observability-plan.md before building anything. For each of my 4 SLOs it lists the metric that measures it, where the metric comes from (api or worker), and the PromQL query that turns it into a percentage. Also sketched the dashboard layout.

## What broke or surprised me
The stopped-worker test from yesterday has a catch. If the worker is the thing reporting how many orders are pending, then when it dies it stops reporting. So the queue metric alone can't catch a dead worker. Prometheus marking the worker target as down is what covers that, so the dashboard needs to show both.

Also, histogram buckets have to line up with the SLO thresholds (0.5s and 30s), otherwise "under 500 ms" can't be measured exactly.

## What I tried (including what didn't work)
Nothing built yet, this was design only.

## Decision and why
- Prometheus client libraries instead of OpenTelemetry for now. Two services don't need a collector, and it's less to learn and break. Can switch later if I add tracing.
- The worker counts pending orders itself instead of adding a separate exporter container.
- Grafana datasource and dashboard provisioned from files in the repo so the setup is repeatable.

## Evidence
docs/observability-plan.md
