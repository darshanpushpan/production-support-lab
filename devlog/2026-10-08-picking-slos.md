# Title: Picking SLOs before writing any code
Date: 2026-10-08

## What I did
Wrote docs/slos.md with 4 targets: API availability (99.5%), API latency (95% of POST /orders under 500 ms), order processing time (99% within 30 seconds) and no lost orders.

## What broke or surprised me
The API can be 100% up while the worker is dead. Orders would still be accepted and just pile up in the database, and availability and latency would both look fine. That's why I added the processing time SLO.

## What I tried (including what didn't work)
Nothing built yet, this was planning only.

## Decision and why
I picked 99.5% availability on purpose instead of 99.9%. This runs on one laptop with no redundancy, so 99.9% would just give me alerts I can't meet. I also went with 500 ms for latency instead of something stricter so normal slow moments don't fire alerts.

## Evidence
docs/slos.md
