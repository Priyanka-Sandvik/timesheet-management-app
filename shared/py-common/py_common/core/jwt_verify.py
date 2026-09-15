"""RS256 JWT verification via a JWKS URL, reusable as FastAPI dependencies.

Used by all three services (Profile, Task, Timelog) to verify the Bearer JWT issued by
Profile Service. Reads the `sub` (email) and `isAdmin` claims from the verified token.
Admin-only routes should depend on `require_admin` (403s if `isAdmin` is not True).

Every service verifies the JWT itself — there is no gateway and no callback to Profile
Service for this check (architecture doc §9).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
import jwt
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


class JwtVerifier:
    """Verifies RS256 JWTs against a JWKS URL and produces `AuthenticatedUser` objects.

    Instantiate once per service (module-level singleton) with that service's configured
    `JWKS_URL`, then use `.require_user` / `.require_admin` as FastAPI dependencies.
    """

    def __init__(self, jwks_url: str, issuer: str | None = None, leeway_seconds: int = 30) -> None:
        self._jwks_url = jwks_url
        self._issuer = issuer
        self._leeway_seconds = leeway_seconds

    def _decode(self, token: str) -> dict:
        try:
            signing_key = _jwks_cache.get_signing_key(self._jwks_url, token)
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

        try:
            options = {"require": ["exp", "sub"]}
            claims = jwt.decode(
                token,
                signing_key.key,
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
    """Convenience factory. Returns (verifier, require_user_dep, require_admin_dep).

    Usage in a service's app/core/jwt.py:
        verifier, require_user, require_admin = build_jwt_dependencies(settings.JWKS_URL)
    Then in routers: `user: AuthenticatedUser = Depends(require_user)` or `Depends(require_admin)`.
    """
    verifier = JwtVerifier(jwks_url=jwks_url, issuer=issuer)
    require_admin = verifier.build_require_admin()
    return verifier, verifier.require_user, require_admin
