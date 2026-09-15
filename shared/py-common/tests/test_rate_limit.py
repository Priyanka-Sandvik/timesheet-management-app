"""Unit tests: in-memory sliding-window rate limiter behavior."""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from py_common.core.rate_limit import SlidingWindowRateLimiter


def _fake_request(ip: str = "1.2.3.4"):
    return SimpleNamespace(client=SimpleNamespace(host=ip), headers={})


def test_allows_up_to_limit_then_blocks():
    limiter = SlidingWindowRateLimiter(calls_per_minute=3, window_seconds=60.0)
    req = _fake_request()

    for _ in range(3):
        limiter.check(req)  # should not raise

    with pytest.raises(HTTPException) as exc_info:
        limiter.check(req)
    assert exc_info.value.status_code == 429


def test_separate_ips_have_independent_windows():
    limiter = SlidingWindowRateLimiter(calls_per_minute=1, window_seconds=60.0)
    req_a = _fake_request("1.1.1.1")
    req_b = _fake_request("2.2.2.2")

    limiter.check(req_a)
    limiter.check(req_b)  # different IP, should not raise

    with pytest.raises(HTTPException):
        limiter.check(req_a)
    with pytest.raises(HTTPException):
        limiter.check(req_b)


def test_window_slides_and_allows_again_after_expiry(monkeypatch):
    limiter = SlidingWindowRateLimiter(calls_per_minute=1, window_seconds=0.05)
    req = _fake_request()

    limiter.check(req)
    with pytest.raises(HTTPException):
        limiter.check(req)

    time.sleep(0.06)
    limiter.check(req)  # window has slid past the old hit, should not raise


def test_falls_back_to_x_forwarded_for_when_no_client():
    limiter = SlidingWindowRateLimiter(calls_per_minute=1, window_seconds=60.0)
    req = SimpleNamespace(client=None, headers={"x-forwarded-for": "9.9.9.9, 8.8.8.8"})

    limiter.check(req)
    with pytest.raises(HTTPException):
        limiter.check(req)


def test_reset_clears_counters():
    limiter = SlidingWindowRateLimiter(calls_per_minute=1, window_seconds=60.0)
    req = _fake_request()
    limiter.check(req)
    limiter.reset()
    limiter.check(req)  # should not raise after reset
