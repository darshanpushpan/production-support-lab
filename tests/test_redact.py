import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))

from logsetup import RedactingJsonFormatter, luhn_ok, redact  # noqa: E402


def test_email_is_masked():
    assert redact("contact test-customer-7@example.com now") == "contact [EMAIL] now"


def test_card_with_spaces_is_masked():
    assert redact("pay with 4111 1111 1111 1111") == "pay with [CARD ****1111]"


def test_card_with_dashes_and_no_separators():
    assert redact("4111-1111-1111-1111") == "[CARD ****1111]"
    assert redact("4111111111111111") == "[CARD ****1111]"


def test_long_number_that_fails_luhn_is_left_alone():
    # 16 digits but not a valid card number, e.g. a tracking number
    assert not luhn_ok("1234567812345678")
    assert redact("tracking 1234567812345678") == "tracking 1234567812345678"


def test_order_ids_and_timestamps_are_not_touched():
    text = '{"time": "2026-10-27T14:03:11.120+00:00", "order_id": 48213}'
    assert redact(text) == text


def test_formatter_redacts_extra_fields_and_stays_valid_json():
    record = logging.LogRecord("api", logging.INFO, __file__, 1, "order created", None, None)
    record.fields = {
        "order_id": 1,
        "email": "test-customer-7@example.com",
        "notes": "pay with 4111 1111 1111 1111",
    }
    line = RedactingJsonFormatter("api").format(record)
    entry = json.loads(line)  # still valid JSON after redaction
    assert entry["email"] == "[EMAIL]"
    assert entry["notes"] == "pay with [CARD ****1111]"
    assert "example.com" not in line
    assert "4111 1111" not in line


def test_formatter_redacts_tracebacks():
    try:
        raise ValueError("bad order for test-customer-7@example.com")
    except ValueError:
        record = logging.LogRecord(
            "api", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )
    line = RedactingJsonFormatter("api").format(record)
    assert "example.com" not in line
