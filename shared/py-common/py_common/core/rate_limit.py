"""In-memory, per-client-IP sliding-window rate limiter — no external dependencies
(no slowapi, no Redis). Designed for Profile Service's auth routes (architecture doc §9,
§2 decision 7, §3.6).

Known limitation (documented, acceptable at this scale): state is process-local. If a
service scales to more than one replica, each replica enforces the limit independently,
so the effective limit is `calls_per_minute * replica_count`. Pin `minReplicas`/`maxReplicas`
to 1 for Profile Service if this ever matters, or move to a shared store later.
"""
from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window counter keyed by client IP."""

    def __init__(self, calls_per_minute: int, window_seconds: float = 60.0) -> None:
        self._calls_per_minute = calls_per_minute
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def _client_key(self, request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return "unknown"

    def check(self, request: Request) -> None:
        key = self._client_key(request)
        now = time.monotonic()
        with self._lock:
            window = self._hits.setdefault(key, deque())
            cutoff = now - self._window_seconds
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= self._calls_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please try again later.",
                    },
                )
            window.append(now)

    def as_dependency(self):
        """Returns a FastAPI-dependency-compatible callable, e.g.:
        `Depends(limiter.as_dependency())` on a route.
        """

        def _dependency(request: Request) -> None:
            self.check(request)

        return _dependency

    def reset(self) -> None:
        """Test helper: clears all counters."""
        with self._lock:
            self._hits.clear()
