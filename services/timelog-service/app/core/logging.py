"""Thin wrapper around py_common's logging setup, scoped to this service's name."""
from __future__ import annotations

import logging

from py_common.core.logging import log_event, setup_logging

SERVICE_NAME = "timelog-service"


def configure_logging() -> logging.Logger:
    return setup_logging(SERVICE_NAME)


__all__ = ["configure_logging", "log_event", "SERVICE_NAME"]
