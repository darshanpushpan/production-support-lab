import os
import time

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily
from pydantic import BaseModel, Field

from logsetup import setup_logging

DATABASE_URL = os.environ["DATABASE_URL"]

log = setup_logging("api")

app = FastAPI(title="Orders API")

# SLO 1 (availability) and SLO 2 (latency) come from these two metrics.
# Buckets include 0.5 so "under 500 ms" can be measured exactly.
REQUESTS = Counter(
    "http_requests_total", "HTTP requests handled", ["handler", "method", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Time spent handling a request",
    ["handler", "method"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


class QueueCollector:
    """Reads the order queue straight from Postgres every time Prometheus scrapes the API.

    This used to live in the worker, but a dead worker can't report its own queue:
    the numbers just disappeared while 3014 orders piled up. The API doesn't depend
    on the worker, so it keeps reporting when the worker is down.
    """

    def collect(self):
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
                count, oldest = conn.execute(
                    "SELECT count(*), COALESCE(EXTRACT(EPOCH FROM now() - min(created_at)), 0) "
                    "FROM orders WHERE status = 'pending'"
                ).fetchone()
        except psycopg.OperationalError:
            log.warning("queue metrics skipped, database unreachable")
            return  # database down: report nothing, the health check covers that
        pending = GaugeMetricFamily("orders_pending", "Orders waiting to be processed")
        pending.add_metric([], count)
        yield pending
        age = GaugeMetricFamily(
            "orders_oldest_pending_seconds", "Age of the oldest pending order (0 if none)"
        )
        age.add_metric([], float(oldest))
        yield age


REGISTRY.register(QueueCollector())


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500  # if the handler crashes, count it as a 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # use the route template (/orders/{order_id}) not the real path,
        # otherwise every order id becomes its own time series
        route = request.scope.get("route")
        handler = route.path if route else "unmatched"
        LATENCY.labels(handler, request.method).observe(time.perf_counter() - start)
        REQUESTS.labels(handler, request.method, str(status)).inc()


class OrderIn(BaseModel):
    customer: str = Field(min_length=1, max_length=100)
    item: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1000)
    email: str = Field(min_length=3, max_length=200)
    notes: str = Field(default="", max_length=500)


def get_conn():
    return psycopg.connect(DATABASE_URL)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    # healthy only if the database answers, not just because the process is up
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError:
        log.error("health check failed, database unreachable")
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok"}


@app.post("/orders", status_code=201)
def create_order(order: OrderIn):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO orders (customer, email, item, quantity, notes) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id, status, created_at",
            (order.customer, order.email, order.item, order.quantity, order.notes),
        ).fetchone()
    # email and notes go in on purpose: this is the kind of line that leaks
    # personal data in real systems. The formatter masks it before it's written.
    log.info("order created", extra={"fields": {
        "order_id": row[0], "customer": order.customer, "email": order.email,
        "item": order.item, "quantity": order.quantity, "notes": order.notes,
    }})
    return {"id": row[0], "status": row[1], "created_at": row[2]}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, customer, item, quantity, status, created_at, processed_at "
            "FROM orders WHERE id = %s",
            (order_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="order not found")
    keys = ["id", "customer", "item", "quantity", "status", "created_at", "processed_at"]
    return dict(zip(keys, row))
