"""Constructs the JwtVerifier dependencies (for verifying Profile Service's tokens), wired
up from this service's Settings.

Timelog Service does NOT issue tokens; it only verifies tokens issued by Profile Service
against Profile Service's JWKS_URL (architecture doc §9).
"""
from __future__ import annotations

from py_common.core.jwt_verify import build_jwt_dependencies

from app.config import Settings


def build_jwt_verifier_dependencies(settings: Settings):
    """Returns (verifier, require_user, require_admin) for verifying Profile Service's
    tokens on all Timelog Service routes, with admin gating applied locally only where
    required (the monthly export route).
    """
    return build_jwt_dependencies(jwks_url=settings.JWKS_URL, issuer=None)
