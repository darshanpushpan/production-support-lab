# Runbook: WorkerDown

**Alert:** `up{job="worker"} == 0` for 1 minute. Prometheus can't scrape the worker.
**Impact:** orders are still accepted by the API (it returns 201) but nothing processes them. They pile up as pending. Customers don't see an error, so nobody will report this.
**Related alerts:** OrdersBacklog fires about 2 to 3 minutes later, OrdersLost after 10 minutes.

## 1. Confirm it

```
docker compose ps worker
docker compose logs worker --tail 50
```

- Status `Exited`: the worker crashed or was stopped. Check the last log lines for a Python traceback.
- Status `Up` but alert firing: the process is alive but Prometheus can't reach port 9100. Check `http://127.0.0.1:9090/targets` for the scrape error.

## 2. Check how bad it is

```
docker compose exec db psql -U orders_app -d orders -c "SELECT count(*), now() - min(created_at) AS oldest FROM orders WHERE status = 'pending';"
```

Or look at the "orders pending" and "SLO 4" panels in Grafana. These come from the API, so they still work while the worker is down.

## 3. Fix

```
docker compose start worker
```

If it exits again straight away, read the traceback in the logs before restarting it in a loop. Common causes so far: database not reachable (the worker logs `database error, retrying in 5s` and keeps retrying, it doesn't exit for that).

## 4. Confirm recovery

- `worker` panel back to UP, alert shows RESOLVED in the alert receiver logs
- `orders pending` going down. The worker handles about 5 orders a second (0.2s per order), so 3000 orders takes about 10 minutes to clear.
- OrdersBacklog and OrdersLost resolve once the oldest pending order is under their thresholds.

## 5. After

SLO 3 (processed within 30 s) will drop once the backlog clears, because every order that waited counts as slow at the moment it finishes. That's expected. Note the incident window and how many orders were affected.
