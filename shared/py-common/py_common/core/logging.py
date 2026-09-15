"""Structured logging setup helper, shared across all three services.

Emits JSON-formatted log lines to stdout (suitable for Application Insights / Container
Apps log collection) and provides a helper for structured audit events (e.g. task imports,
per architecture doc §9: "Log every task import ... as structured events").
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(service_name: str, level: int = logging.INFO) -> logging.Logger:
    """Configures root logging with a JSON stdout handler and returns a named logger.

    Call once at service startup (e.g. in app/main.py or app/core/logging.py wrapper).
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)

    logger = logging.getLogger(service_name)
    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Logs a structured audit event, e.g.:
    log_event(logger, "task_import", user=email, imported=5, skipped=1, errors=2)
    """
    logger.info(event, extra={"extra_fields": {"event": event, **fields}})
