-- init.sql only runs on a brand new volume, so existing databases need this.
-- Run with: docker compose exec -T db psql -U <user> -d orders < db/migrations/002-email-notes.sql
ALTER TABLE orders ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT '';
