"""Constructs the JwtVerifier dependencies (for verifying Profile Service's tokens), wired
up from this service's Settings.

Timelog Service does NOT issue tokens; it only verifies tokens issued by Profile Service
(architecture doc §9). In local dev (USE_LOCAL_KEY=true) it fetches Profile Service's
JWKS_URL; in production it reads the public key + kid directly from Azure Key Vault.
"""
from __future__ import annotations

from py_common.core.jwt_verify import build_jwt_dependencies, build_jwt_dependencies_from_key_vault

from app.config import Settings


def build_jwt_verifier_dependencies(settings: Settings):
    """Returns (verifier, require_user, require_admin) for verifying Profile Service's
    tokens on all Timelog Service routes, with admin gating applied locally only where
    required (the monthly export route).
    """
    if settings.USE_LOCAL_KEY:
        return build_jwt_dependencies(jwks_url=settings.JWKS_URL, issuer=None)
    return build_jwt_dependencies_from_key_vault(
        key_vault_url=settings.KEY_VAULT_URL,
        public_key_secret_name=settings.JWT_PUBLIC_KEY_SECRET_NAME,
        kid_secret_name=settings.JWT_KID_SECRET_NAME,
        issuer=None,
    )
