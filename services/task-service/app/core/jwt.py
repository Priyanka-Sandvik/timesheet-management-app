"""Constructs the JWT verification dependencies (require_user / require_admin) from
py_common, wired up from this service's Settings.

Task Service does NOT issue tokens - it only verifies tokens issued by Profile Service
against Profile Service's JWKS_URL. Admin gating (isAdmin claim) is 100% local: this
service never calls back to Profile Service to check admin status.
"""
from __future__ import annotations

from py_common.core.jwt_verify import build_jwt_dependencies

from app.config import Settings


def build_jwt_verifier_dependencies(settings: Settings):
    """Returns (verifier, require_user, require_admin) FastAPI dependencies."""
    return build_jwt_dependencies(jwks_url=settings.JWKS_URL, issuer=settings.JWT_ISSUER)
