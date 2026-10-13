import os

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DATABASE_URL = os.environ["DATABASE_URL"]

app = FastAPI(title="Orders API")


class OrderIn(BaseModel):
    customer: str = Field(min_length=1, max_length=100)
    item: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=1000)


def get_conn():
    return psycopg.connect(DATABASE_URL)


@app.get("/health")
def health():
    # healthy only if the database answers, not just because the process is up
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok"}


@app.post("/orders", status_code=201)
def create_order(order: OrderIn):
    with get_conn() as conn:
        row = conn.execute(
            "INSERT INTO orders (customer, item, quantity) VALUES (%s, %s, %s) "
            "RETURNING id, status, created_at",
            (order.customer, order.item, order.quantity),
        ).fetchone()
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
