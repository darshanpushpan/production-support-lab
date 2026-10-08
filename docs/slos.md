# Service Level Objectives

The app takes orders through an API, stores them in Postgres, and a worker processes them in the background.
These are the targets I'm going to monitor and alert on. Nothing is measured yet, so this is the plan, not results.
All of them use a rolling 7 day window.

## 1. API availability
- SLI: % of requests to /orders that don't return a 5xx error
- Target: 99.5%
- Error budget: about 50 minutes of failed requests per week
- Why: this runs on one laptop with no redundancy. 99.9% is what a lot of real production systems aim for, but copying it here would just mean alerts I can't meet. I'd rather pick a target that matches the setup and tighten it later if the numbers allow.
- How I'll measure it: a request counter in Prometheus, labelled by status code

## 2. API latency
- SLI: % of POST /orders requests that finish in under 500 ms
- Target: 95%
- Why: placing an order shouldn't feel slow. 500 ms leaves room so a normal busy moment doesn't page anyone. I'll revisit the number once I have real data.
- How I'll measure it: a request duration histogram in Prometheus

## 3. Order processing time
- SLI: % of orders the worker finishes within 30 seconds of being created
- Target: 99%
- Why: the API can be completely up while the worker is dead. Orders would still be accepted and just pile up, and the first two SLOs would look perfect. This one is there to catch that.
- How I'll measure it: time between created_at and processed_at, plus a gauge for how many jobs are waiting

## 4. No lost orders
- SLI: every accepted order ends up either processed or marked failed
- Target: 100%
- Why: a slow order is annoying, a lost one is a real problem for the business.
- How I'll measure it: a SQL check for orders stuck in "pending" for more than 10 minutes

## Not measuring yet
- Database performance on its own. If the database gets slow, the latency and processing time SLOs should show it from the user's side first.
