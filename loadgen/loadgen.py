"""Sends a steady trickle of fake orders so the dashboards have something to show."""
import json
import os
import random
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("API_URL", "http://api:8000")
ORDERS_PER_MINUTE = float(os.environ.get("ORDERS_PER_MINUTE", "30"))
ITEMS = ["keyboard", "mouse", "monitor", "headset", "webcam", "dock"]
NOTES = ["", "", "", "leave at side door", "gift wrap please", "call before delivery"]
# Visa's published test number, not a real card. Some orders put it in the notes,
# like a customer typing their card where they shouldn't. The logs must never show it.
TEST_CARD = "4111 1111 1111 1111"


def send_order():
    n = random.randint(1, 50)
    notes = random.choice(NOTES)
    if random.random() < 0.05:
        notes = f"pay with {TEST_CARD}"
    body = json.dumps({
        "customer": f"test-customer-{n}",  # obviously fake data only
        "email": f"test-customer-{n}@example.com",  # example.com is reserved for tests
        "item": random.choice(ITEMS),
        "quantity": random.randint(1, 3),
        "notes": notes,
    }).encode()
    req = urllib.request.Request(
        f"{API_URL}/orders", data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError):
        return "unreachable"


if __name__ == "__main__":
    print(f"loadgen sending ~{ORDERS_PER_MINUTE:g} orders/min to {API_URL}", flush=True)
    while True:
        status = send_order()
        if status != 201:
            print(f"order failed: {status}", flush=True)
        time.sleep(random.expovariate(ORDERS_PER_MINUTE / 60))
