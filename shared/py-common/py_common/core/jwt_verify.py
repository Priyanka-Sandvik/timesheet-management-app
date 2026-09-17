"""RS256 JWT verification, reusable as FastAPI dependencies.

Used by all three services (Profile, Task, Timelog) to verify the Bearer JWT issued by
Profile Service. Reads the `sub` (email) and `isAdmin` claims from the verified token.
Admin-only routes should depend on `require_admin` (403s if `isAdmin` is not True).

Every service verifies the JWT itself — there is no gateway and no callback to Profile
Service for this check (architecture doc §9).

The signing key is obtained from a `PublicKeySource`:
- `JwksHttpPublicKeySource`: fetches Profile Service's `/.well-known/jwks.json` over HTTP.
  Used for local dev / docker-compose (`USE_LOCAL_KEY=true`).
- `KeyVaultPublicKeySource`: reads the public key + kid directly from Azure Key Vault
  secrets. Used in production — no JWKS endpoint call needed, and Profile Service's own
  `/.well-known/jwks.json` route is not required for inter-service verification.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
import jwt
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    email: str
    is_admin: bool
    full_name: str | None = None
    raw_claims: dict | None = None


class _JwksCache:
    """Thin cache wrapper around PyJWT's PyJWKClient, itself cached by kid.

    PyJWKClient already caches keys by kid; we additionally cache the client instance
    per jwks_url and re-create it if the underlying jwks_url changes (unlikely, but keeps
    this safe to use as a module-level singleton across requests).
    """

    def __init__(self) -> None:
        self._clients: dict[str, PyJWKClient] = {}

    def get_signing_key(self, jwks_url: str, token: str):
        client = self._clients.get(jwks_url)
        if client is None:
            client = PyJWKClient(jwks_url, cache_keys=True, lifespan=300)
            self._clients[jwks_url] = client
        return client.get_signing_key_from_jwt(token)


_jwks_cache = _JwksCache()


class PublicKeySource(ABC):
    """Abstraction over "where the RS256 verification key comes from"."""

    @abstractmethod
    def get_signing_key(self, token: str) -> str | bytes:
        """Return the PEM-encoded public key (or key object) that should verify `token`."""


class JwksHttpPublicKeySource(PublicKeySource):
    """Fetches the signing key from a JWKS URL, matched by the token's `kid` header.

    Used for local dev / docker-compose, where services fetch Profile Service's
    `/.well-known/jwks.json` over HTTP.
    """

    def __init__(self, jwks_url: str) -> None:
        self._jwks_url = jwks_url

    def get_signing_key(self, token: str) -> str | bytes:
        try:
            return _jwks_cache.get_signing_key(self._jwks_url, token).key
        except jwt.PyJWKClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": f"Unable to fetch signing key: {exc}"},
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": f"Unable to reach JWKS endpoint: {exc}"},
            ) from exc


class KeyVaultPublicKeySource(PublicKeySource):
    """Reads the public key + kid directly from Azure Key Vault secrets.

    Eliminates the need for a JWKS endpoint in production: every service reads the same
    Key Vault secrets that Profile Service's `KeyVaultKeySource` reads for signing, via its
    own Managed Identity (read-only RBAC). The token's `kid` header is checked against the
    Key Vault kid so a rotated key is detected instead of silently verified with a stale
    cached key.
    """

    def __init__(
        self,
        key_vault_url: str,
        public_key_secret_name: str,
        kid_secret_name: str,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._public_key_secret_name = public_key_secret_name
        self._kid_secret_name = kid_secret_name
        self._cache_ttl_seconds = cache_ttl_seconds
        self._client = SecretClient(vault_url=key_vault_url, credential=DefaultAzureCredential())
        self._cache: dict[str, tuple[float, str]] = {}

    def _get_secret(self, name: str) -> str:
        cached = self._cache.get(name)
        now = time.monotonic()
        if cached is not None and now - cached[0] < self._cache_ttl_seconds:
            return cached[1]
        try:
            value = self._client.get_secret(name).value
        except Exception as exc:  # Azure SDK raises various HttpResponseError subclasses.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": f"Unable to fetch key from Key Vault: {exc}"},
            ) from exc
        if not value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": f"Key Vault secret '{name}' is missing or empty"},
            )
        self._cache[name] = (now, value)
        return value

    def get_signing_key(self, token: str) -> str | bytes:
        public_key_pem = self._get_secret(self._public_key_secret_name)
        expected_kid = self._get_secret(self._kid_secret_name)
        token_kid = jwt.get_unverified_header(token).get("kid")
        if token_kid is not None and token_kid != expected_kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "Token 'kid' does not match the current signing key"},
            )
        return public_key_pem


class JwtVerifier:
    """Verifies RS256 JWTs against a `PublicKeySource` and produces `AuthenticatedUser` objects.

    Instantiate once per service (module-level singleton), then use `.require_user` /
    `.require_admin` as FastAPI dependencies. Pass either `jwks_url` (local dev) or
    `key_source` (production, Key Vault-backed) — exactly one is required.
    """

    def __init__(
        self,
        jwks_url: str | None = None,
        key_source: PublicKeySource | None = None,
        issuer: str | None = None,
        leeway_seconds: int = 30,
    ) -> None:
        if (jwks_url is None) == (key_source is None):
            raise ValueError("JwtVerifier requires exactly one of jwks_url or key_source")
        self._key_source = key_source if key_source is not None else JwksHttpPublicKeySource(jwks_url)
        self._issuer = issuer
        self._leeway_seconds = leeway_seconds

    def _decode(self, token: str) -> dict:
        signing_key = self._key_source.get_signing_key(token)

        try:
            options = {"require": ["exp", "sub"]}
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                leeway=self._leeway_seconds,
                options=options,
            )
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "Token expired"},
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": f"Invalid token: {exc}"},
            ) from exc
        return claims

    def _extract_bearer_token(self, credentials: HTTPAuthorizationCredentials | None) -> str:
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "Missing bearer token"},
            )
        return credentials.credentials

    def require_user(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> AuthenticatedUser:
        """FastAPI dependency: verifies the token and returns the authenticated user.
        Does NOT check isAdmin — use `require_admin` for admin-only routes.
        """
        token = self._extract_bearer_token(credentials)
        claims = self._decode(token)
        email = claims.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "Token missing 'sub' claim"},
            )
        user = AuthenticatedUser(
            email=email,
            is_admin=bool(claims.get("isAdmin", False)),
            full_name=claims.get("fullName"),
            raw_claims=claims,
        )
        request.state.user = user
        return user

    def build_require_admin(self):
        """Returns a FastAPI-dependency-compatible callable enforcing isAdmin==True.

        Constructed dynamically because FastAPI's Depends() needs a bound reference to
        `self.require_user`, which only exists once the instance is created.
        """

        def _require_admin(user: AuthenticatedUser = Depends(self.require_user)) -> AuthenticatedUser:
            if not user.is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"code": "FORBIDDEN", "message": "Admin privileges required"},
                )
            return user

        return _require_admin


def build_jwt_dependencies(jwks_url: str, issuer: str | None = None) -> tuple[JwtVerifier, object, object]:
    """Convenience factory for local dev / docker-compose. Returns (verifier, require_user_dep,
    require_admin_dep).

    Usage in a service's app/core/jwt.py:
        verifier, require_user, require_admin = build_jwt_dependencies(settings.JWKS_URL)
    Then in routers: `user: AuthenticatedUser = Depends(require_user)` or `Depends(require_admin)`.
    """
    verifier = JwtVerifier(jwks_url=jwks_url, issuer=issuer)
    require_admin = verifier.build_require_admin()
    return verifier, verifier.require_user, require_admin


def build_jwt_dependencies_from_key_vault(
    key_vault_url: str,
    public_key_secret_name: str,
    kid_secret_name: str,
    issuer: str | None = None,
    cache_ttl_seconds: int = 300,
) -> tuple[JwtVerifier, object, object]:
    """Convenience factory for production. Reads the public key + kid directly from Azure
    Key Vault (no JWKS endpoint call). Returns (verifier, require_user_dep, require_admin_dep).

    Usage in a service's app/core/jwt.py:
        verifier, require_user, require_admin = build_jwt_dependencies_from_key_vault(
            settings.KEY_VAULT_URL, settings.JWT_PUBLIC_KEY_SECRET_NAME, settings.JWT_KID_SECRET_NAME,
        )
    """
    key_source = KeyVaultPublicKeySource(
        key_vault_url=key_vault_url,
        public_key_secret_name=public_key_secret_name,
        kid_secret_name=kid_secret_name,
        cache_ttl_seconds=cache_ttl_seconds,
    )
    verifier = JwtVerifier(key_source=key_source, issuer=issuer)
    require_admin = verifier.build_require_admin()
    return verifier, verifier.require_user, require_admin
