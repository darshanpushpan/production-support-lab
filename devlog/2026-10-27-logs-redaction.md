# Title: Logs in Loki, and a card number that only got half hidden
Date: 2026-10-27

## What I did
- api and worker now write JSON logs, one object per line, to stdout and to a shared volume (/var/log/app).
- common/logsetup.py masks emails and card numbers before a line is written anywhere. Emails become [EMAIL], cards become [CARD ****1111].
- Orders now have an email and a notes field, so there is actual personal data going through the system. loadgen uses test-customer-N@example.com and puts Visa's test number (4111 1111 1111 1111) in about 5% of order notes, like a customer typing their card in the wrong box.
- Grafana Alloy tails the log files and pushes them to Loki. Loki keeps 7 days. Added a Loki datasource and a logs panel at the bottom of the SLO dashboard.
- 7 pytest tests for the redaction.
- Migration 002 adds the new columns, because init.sql only runs on a fresh volume and mine has 6000+ orders in it.

## What broke or surprised me
1. The logs are clean, but the database isn't. Loki has 0 lines with the raw card number or an @example.com email. But orders 6065 and 6076 have "pay with 4111 1111 1111 1111" sitting in Postgres in plain text. Redacting logs doesn't fix where the data is stored.
2. A plain "13 to 19 digits" regex would also hide normal long numbers like tracking numbers. Real card numbers pass the Luhn checksum, so I only mask numbers that pass it. 1234567812345678 is 16 digits and stays visible.
3. The redaction has to run on the whole finished line, not just the message. The email was in an extra field, not in "order created", so filtering only the message would have missed it. Same for tracebacks, there's a test for that.

## What I tried (including what didn't work)
- First idea was letting Alloy read every container's logs through the Docker socket. Less setup, but that socket is basically admin access to Docker. Went with a shared log folder instead, mounted read only into Alloy.
- Checked end to end, not just with tests: queried Loki for "4111 1111" and "@example.com" over the last 30 minutes, both 0 results. Queried for "CARD" and got the masked lines for the same order ids that have the raw number in the database.

## Decision and why
- Redact in the app, before the line is written, not later in Alloy. If it's done in Alloy the raw value is still in the file on disk and in docker logs.
- Only level and service are Loki labels. Order ids and customers stay inside the line, otherwise every order would be its own stream.
- Log files rotate at 5 MB, 3 old files, so logs can't fill the volume.

## Evidence
- devlog/evidence/2026-10-27-redaction.txt (Postgres vs Loki for the same orders, zero raw matches, pytest output)
- common/logsetup.py, tests/test_redact.py
- observability/alloy/config.alloy, observability/loki/loki.yml

## Not sure yet
- Should the API refuse or mask card numbers in notes before saving them? Probably yes. Leaving it for the security pass.
- uvicorn's own access log lines still go to stdout only, not to the file, so Loki doesn't have them. Prometheus already covers requests, so maybe that's fine.
- Redaction only knows emails and cards. Phone numbers and addresses would go straight through.
