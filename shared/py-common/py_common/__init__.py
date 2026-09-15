"""Shared cross-cutting utilities for the Timesheet Management Application microservices.

Modules:
- py_common.core.errors: standard error envelope + FastAPI exception handlers
- py_common.core.jwt_issue: RS256 JWT issuance (Profile Service only) + KeySource abstraction
- py_common.core.jwt_verify: RS256 JWT verification via JWKS, FastAPI auth dependencies
- py_common.core.table_client: Azure Table Storage client factory
- py_common.core.rate_limit: in-memory sliding-window rate limiter dependency
- py_common.core.logging import setup_logging: structured logging setup
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
