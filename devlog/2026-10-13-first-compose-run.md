# Title: Getting the API, worker and Postgres running in Docker Compose
Date: 2026-10-13

## What I did
Set up docker-compose.yml with three services: Postgres 16, a FastAPI orders API and a Python worker.
- API: POST /orders saves an order as pending, GET /orders/{id} returns it, /health checks that the database actually answers (not just that the process is up).
- Worker: polls for pending orders every 2 seconds, marks them processed and sets processed_at.
- Postgres creates the orders table from db/init.sql on first start. The API and worker wait for the db healthcheck before starting.
- Sent a test order with curl and it went from pending to processed.

## What broke or surprised me
First docker command failed because Docker Desktop wasn't running ("open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified"). After starting it the stack came up on the first build.

Then I tested the gap from my SLOs on purpose. I stopped the worker and sent an order. /health still said ok and the API returned 201, but the order sat in pending until I started the worker again (about 13 seconds). That's exactly the case availability and latency can't see, so the processing time SLO is going to matter.

## What I tried (including what didn't work)
Nothing failed apart from Docker Desktop not being started.

## Decision and why
- Postgres is the job queue, no Redis or RabbitMQ. The worker grabs orders with SELECT ... FOR UPDATE SKIP LOCKED so two workers would never process the same order. One less service to run and monitor.
- All ports are bound to 127.0.0.1 so nothing is reachable from outside my laptop.
- Password lives in .env (gitignored), with .env.example committed.
- Containers run as a non-root user.
- If the database drops, the worker waits and reconnects instead of crashing.

## Evidence
- devlog/evidence/2026-10-13-worker-stopped.txt
- devlog/evidence/2026-10-13-compose-ps.txt
