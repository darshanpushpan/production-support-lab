-- Runs once, the first time the Postgres volume is created.
CREATE TABLE IF NOT EXISTS orders (
    id           SERIAL PRIMARY KEY,
    customer     TEXT        NOT NULL,
    email        TEXT,
    item         TEXT        NOT NULL,
    quantity     INTEGER     NOT NULL CHECK (quantity > 0),
    notes        TEXT        NOT NULL DEFAULT '',
    status       TEXT        NOT NULL DEFAULT 'pending',  -- pending, processed, failed
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

-- the worker looks for pending orders oldest first
CREATE INDEX IF NOT EXISTS idx_orders_pending ON orders (created_at) WHERE status = 'pending';
