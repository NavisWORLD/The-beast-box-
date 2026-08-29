from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Mapping

_SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "PRIVATE_KEY")


def redact_mapping(values: Mapping[str, object]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for key, value in values.items():
        upper = key.upper()
        if any(marker in upper for marker in _SECRET_MARKERS):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, Mapping):
            redacted[key] = redact_mapping(value)
        else:
            redacted[key] = value
    return redacted


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, Mapping):
            payload["event_data"] = redact_mapping(event_data)
        return json.dumps(payload, sort_keys=True, default=str)


def configure_logging(json_output: bool = False, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("beastbox")
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(level)
    if json_output:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger
