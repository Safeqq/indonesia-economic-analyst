from __future__ import annotations

import json
import logging
from pathlib import Path

from pipelines.utils.structured_logging import JsonFormatter


def test_json_formatter_emits_context_and_redacts_credentials() -> None:
    record = logging.LogRecord(
        name="pipeline.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg=(
            "request /key/sangat-rahasia BPS_API_KEY=token-rahasia "
            "MYSQL_PASSWORD=password-rahasia "
            "mysql+pymysql://analyst:url-rahasia@database/economic_intelligence"
        ),
        args=(),
        exc_info=None,
    )
    record.event = "pipeline_request"
    record.source_code = "bps"
    record.api_key = "nilai-rahasia"
    record.snapshot = Path("data/raw/bps/snapshot.json")

    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "pipeline_request"
    assert payload["source_code"] == "bps"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["snapshot"] == "data/raw/bps/snapshot.json"
    assert "sangat-rahasia" not in payload["message"]
    assert "token-rahasia" not in payload["message"]
    assert "password-rahasia" not in payload["message"]
    assert "url-rahasia" not in payload["message"]


def test_json_formatter_includes_exception_without_breaking_json() -> None:
    try:
        raise RuntimeError("contoh error")
    except RuntimeError:
        record = logging.LogRecord(
            name="pipeline.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=20,
            msg="operasi gagal",
            args=(),
            exc_info=__import__("sys").exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "ERROR"
    assert "RuntimeError: contoh error" in payload["exception"]
