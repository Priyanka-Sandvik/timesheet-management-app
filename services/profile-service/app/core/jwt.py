"""Constructs the JwtIssuer (for issuing tokens on register/login) and the JwtVerifier
dependencies (for verifying Profile Service's own tokens on GET /api/v1/me), both from
py_common, wired up from this service's Settings.

Switching key sources from local-file to Key Vault is a one-line change here, gated by
USE_LOCAL_KEY.
"""
from __future__ import annotations

from py_common.core.jwt_issue import JwtIssuer, KeyVaultKeySource, LocalFileKeySource
from py_common.core.jwt_verify import build_jwt_dependencies

from app.config import Settings


def build_jwt_issuer(settings: Settings) -> JwtIssuer:
    if settings.USE_LOCAL_KEY:
        key_source = LocalFileKeySource(settings.LOCAL_KEY_DIR)
    else:
        # TODO(prod): KeyVaultKeySource is a stub in py_common and raises NotImplementedError
        # until Key Vault wiring is implemented there. Flip USE_LOCAL_KEY to false only once
        # that lands.
        key_source = KeyVaultKeySource(settings.KEY_VAULT_URL, settings.JWT_KEY_NAME)

    return JwtIssuer(
        key_source=key_source,
        expiry_hours=settings.JWT_EXPIRY_HOURS,
        issuer=settings.JWT_ISSUER,
    )


def build_jwt_verifier_dependencies(settings: Settings):
    """Returns (verifier, require_user, require_admin) for verifying this service's own
    tokens on GET /api/v1/me and the admin-only routes.
    """
    return build_jwt_dependencies(jwks_url=settings.JWKS_URL, issuer=settings.JWT_ISSUER)
