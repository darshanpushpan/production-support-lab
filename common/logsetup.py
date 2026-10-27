"""JSON logging with redaction, shared by the api and the worker.

Every log line is one JSON object, so Loki can filter on fields like level and
service. Before a line is written anywhere (stdout or the log file), emails and
card-like numbers are masked. Redacting the finished line, not just the message,
means extra fields and tracebacks get cleaned too.
"""
import json
import logging
import logging.handlers
import os
import re
import sys
from datetime import datetime, timezone

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# 13 to 19 digits, optionally split by spaces or dashes (4111 1111 1111 1111)
CARD_RE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")


def luhn_ok(digits):
    """Card numbers pass the Luhn checksum. Random long numbers usually don't."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _mask_card(match):
    digits = re.sub(r"\D", "", match.group())
    if luhn_ok(digits):
        return f"[CARD ****{digits[-4:]}]"
    return match.group()  # long number that isn't a card, leave it alone


def redact(text):
    text = EMAIL_RE.sub("[EMAIL]", text)
    return CARD_RE.sub(_mask_card, text)


class RedactingJsonFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, record):
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "service": self.service,
            "msg": record.getMessage(),
        }
        # anything passed as logger.info("...", extra={"fields": {...}})
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return redact(json.dumps(entry, default=str))


def setup_logging(service):
    """Log to stdout (docker logs) and to /var/log/app/<service>.log (Alloy reads this)."""
    formatter = RedactingJsonFormatter(service)
    handlers = [logging.StreamHandler(sys.stdout)]
    log_dir = os.environ.get("LOG_DIR", "/var/log/app")
    if os.path.isdir(log_dir):
        # rotate at 5 MB and keep 3 old files so the volume can't fill up
        handlers.append(logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, f"{service}.log"), maxBytes=5_000_000, backupCount=3
        ))
    root = logging.getLogger()
    root.handlers.clear()
    for h in handlers:
        h.setFormatter(formatter)
        root.addHandler(h)
    root.setLevel(logging.INFO)
    return logging.getLogger(service)
