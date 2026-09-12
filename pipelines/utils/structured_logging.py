from __future__ import annotations

import json
import logging
import logging.config
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "logging.yml"

_STANDARD_RECORD_ATTRIBUTES = set(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|authorization|password|secret|token)", re.IGNORECASE
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(
        r"(?i)((?:api[_-]?key|authorization|password|secret|token)\s*=\s*)"
        r"[^\s,;]+"
    ),
    re.compile(r"(?i)(/key/)[^/?\s]+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"),
    re.compile(r"(?i)(://[^:\s/@]+:)[^@\s/]+(?=@)"),
)


def redact_sensitive_text(value: str) -> str:
    redacted = value
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


def _json_safe(value: Any, *, key: str = "") -> Any:
    if _SENSITIVE_KEY_PATTERN.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): _json_safe(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class JsonFormatter(logging.Formatter):
    """Serialize application logs as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "log"),
            "message": redact_sensitive_text(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRIBUTES and key != "event":
                payload[key] = _json_safe(value, key=key)
        if record.exc_info:
            payload["exception"] = redact_sensitive_text(
                self.formatException(record.exc_info)
            )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    configuration = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    configured_level = os.getenv("LOG_LEVEL", "INFO").upper()
    configuration["root"]["level"] = configured_level
    for handler in configuration.get("handlers", {}).values():
        handler["level"] = configured_level
    logging.config.dictConfig(configuration)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    message: str,
    **context: object,
) -> None:
    logger.log(level, message, extra={"event": event, **context})
