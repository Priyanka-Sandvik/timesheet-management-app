"""Thin re-export of py_common's logging helpers so app code imports from `app.core.logging`
consistently with the other layers, per the required repo layout.
"""
from __future__ import annotations

from py_common.core.logging import log_event, setup_logging

__all__ = ["setup_logging", "log_event"]
