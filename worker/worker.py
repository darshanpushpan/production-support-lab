import os
import time

import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "2"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "10"))

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
            conn.execute(
                "UPDATE orders SET status = 'processed', processed_at = now() WHERE id = %s",
                (order_id,),
            )
    return len(ids)


def main():
    print("worker starting", flush=True)
    while True:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
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
