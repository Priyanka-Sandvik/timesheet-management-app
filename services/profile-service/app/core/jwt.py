"""Constructs the JwtIssuer (for issuing tokens on register/login) and the JwtVerifier
dependencies (for verifying Profile Service's own tokens on GET /api/v1/me), both from
py_common, wired up from this service's Settings.

Switching key sources from local-file to Key Vault is gated by USE_LOCAL_KEY: local dev
uses LocalFileKeySource + a JWKS URL, production uses KeyVaultKeySource + Key Vault secrets
read directly (no JWKS endpoint call, even for Profile Service's own token verification).
"""
from __future__ import annotations

from py_common.core.jwt_issue import JwtIssuer, KeyVaultKeySource, LocalFileKeySource
from py_common.core.jwt_verify import build_jwt_dependencies, build_jwt_dependencies_from_key_vault

from app.config import Settings


def build_jwt_issuer(settings: Settings) -> JwtIssuer:
    if settings.USE_LOCAL_KEY:
        key_source = LocalFileKeySource(settings.LOCAL_KEY_DIR)
    else:
        key_source = KeyVaultKeySource(
            key_vault_url=settings.KEY_VAULT_URL,
            private_key_secret_name=settings.JWT_PRIVATE_KEY_SECRET_NAME,
            public_key_secret_name=settings.JWT_PUBLIC_KEY_SECRET_NAME,
            kid_secret_name=settings.JWT_KID_SECRET_NAME,
        )

    return JwtIssuer(
        key_source=key_source,
        expiry_hours=settings.JWT_EXPIRY_HOURS,
        issuer=settings.JWT_ISSUER,
    )


def build_jwt_verifier_dependencies(settings: Settings):
    """Returns (verifier, require_user, require_admin) for verifying this service's own
    tokens on GET /api/v1/me and the admin-only routes.
    """
    if settings.USE_LOCAL_KEY:
        return build_jwt_dependencies(jwks_url=settings.JWKS_URL, issuer=settings.JWT_ISSUER)
    return build_jwt_dependencies_from_key_vault(
        key_vault_url=settings.KEY_VAULT_URL,
        public_key_secret_name=settings.JWT_PUBLIC_KEY_SECRET_NAME,
        kid_secret_name=settings.JWT_KID_SECRET_NAME,
        issuer=settings.JWT_ISSUER,
    )
