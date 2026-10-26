import os
import time

import psycopg
from prometheus_client import Counter, Histogram, start_http_server

DATABASE_URL = os.environ["DATABASE_URL"]
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "2"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9100"))

# SLO 3: time from order created to processed. Buckets include 30.
PROCESSING = Histogram(
    "order_processing_seconds",
    "Seconds between an order being created and the worker finishing it",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)
PROCESSED = Counter("orders_processed_total", "Orders the worker has processed")
# Queue size and oldest pending order are reported by the API now, not here.
# When the worker died, these numbers died with it.

# SKIP LOCKED means two workers never grab the same order
CLAIM_SQL = """
    SELECT id FROM orders
    WHERE status = 'pending'
    ORDER BY created_at
    LIMIT %s
    FOR UPDATE SKIP LOCKED
"""

def process_batch(conn):
    with conn.transaction():
        ids = [r[0] for r in conn.execute(CLAIM_SQL, (BATCH_SIZE,)).fetchall()]
        for order_id in ids:
            time.sleep(0.2)  # stand-in for real work (payment, stock check, etc.)
            row = conn.execute(
                "UPDATE orders SET status = 'processed', processed_at = now() "
                "WHERE id = %s RETURNING EXTRACT(EPOCH FROM processed_at - created_at)",
                (order_id,),
            ).fetchone()
            PROCESSING.observe(float(row[0]))
            PROCESSED.inc()
    return len(ids)


def main():
    # the worker has no web server of its own, so this gives Prometheus a /metrics to scrape
    start_http_server(METRICS_PORT)
    print(f"worker starting, metrics on :{METRICS_PORT}", flush=True)
    while True:
        try:
            with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
                while True:
                    done = process_batch(conn)
                    if done:
                        print(f"processed {done} orders", flush=True)
                    else:
                        time.sleep(POLL_SECONDS)
        except psycopg.OperationalError as e:
            # database went away; wait and reconnect instead of crashing
            print(f"database error, retrying in 5s: {e}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
