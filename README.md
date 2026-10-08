# Production Support Lab

A small multi-service app that I run, monitor, break on purpose, and support like a production system.

Status: planning (started Oct 2026). This README describes the plan, not finished work. Sections get updated as pieces are actually built.

## Why

My first project, [SupportOps Insight](https://github.com/darshanpushpan/SupportOps-Insight-dashboard), parsed simulated log files. This one generates real telemetry from a running system so I can practise the whole production support loop: detect, ticket, troubleshoot, resolve, write it up.

## Plan

- App: FastAPI web/API service, background worker, Postgres, all in Docker Compose
- Metrics: OpenTelemetry + Prometheus, dashboards in Grafana
- Logs: Loki, with PII redaction
- Alerting: Alertmanager → a small Python bridge → ServiceNow incident (Personal Developer Instance)
- Fault injection: scripts that add DB latency, kill the worker, fill disk, ship a bad deploy
- Runbooks and postmortems for every injected incident
- CI: tests, rule validation, synthetic checks

## Devlog

Progress notes live in [`devlog/`](devlog/). Copy `devlog/TEMPLATE.md` for each entry.
