"""Unit tests: JWT issue/verify roundtrip + admin claim enforcement."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from jwt import PyJWK

from py_common.core.jwt_issue import JwtIssuer, LocalFileKeySource
from py_common.core.jwt_verify import JwtVerifier


@pytest.fixture()
def issuer(tmp_path):
    key_source = LocalFileKeySource(tmp_path / "keys")
    return JwtIssuer(key_source, expiry_hours=8, issuer="profile-service"), key_source


def test_jwt_issue_verify_roundtrip(issuer):
    jwt_issuer, key_source = issuer
    token, expires_in = jwt_issuer.issue_token(email="alice@sandvik.com", is_admin=False, full_name="Alice A")
    assert expires_in == 8 * 3600

    public_pem = key_source.get_public_key_pem()
    claims = jwt.decode(token, public_pem, algorithms=["RS256"], issuer="profile-service")

    assert claims["sub"] == "alice@sandvik.com"
    assert claims["isAdmin"] is False
    assert claims["fullName"] == "Alice A"
    assert "exp" in claims and "iat" in claims


def test_jwt_issue_admin_claim_embedded(issuer):
    jwt_issuer, key_source = issuer
    token, _ = jwt_issuer.issue_token(email="admin@sandvik.com", is_admin=True)
    public_pem = key_source.get_public_key_pem()
    claims = jwt.decode(token, public_pem, algorithms=["RS256"], issuer="profile-service")
    assert claims["isAdmin"] is True


def test_jwks_document_shape(issuer):
    jwt_issuer, key_source = issuer
    jwks = jwt_issuer.get_jwks()
    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert key["kid"] == key_source.get_kid()
    assert "n" in key and "e" in key
    # Public key only — no private material.
    assert "d" not in key


def _build_app_with_auth(verifier: JwtVerifier) -> FastAPI:
    app = FastAPI()
    require_admin = verifier.build_require_admin()

    @app.get("/me")
    def me(user=__import__("fastapi").Depends(verifier.require_user)):
        return {"email": user.email, "isAdmin": user.is_admin}

    @app.get("/admin-only")
    def admin_only(user=__import__("fastapi").Depends(require_admin)):
        return {"email": user.email}

    return app


def _patch_signing_key(monkeypatch, public_pem: bytes, kid: str):
    fake_signing_key = SimpleNamespace(key=public_pem)

    def fake_get_signing_key(self, jwks_url, token):
        return fake_signing_key

    monkeypatch.setattr(
        "py_common.core.jwt_verify._JwksCache.get_signing_key", fake_get_signing_key
    )


def test_admin_claim_enforcement_allows_admin(issuer, monkeypatch):
    jwt_issuer, key_source = issuer
    _patch_signing_key(monkeypatch, key_source.get_public_key_pem(), key_source.get_kid())

    verifier = JwtVerifier(jwks_url="https://fake/jwks.json", issuer="profile-service")
    app = _build_app_with_auth(verifier)
    client = TestClient(app)

    token, _ = jwt_issuer.issue_token(email="admin@sandvik.com", is_admin=True)
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@sandvik.com"


def test_admin_claim_enforcement_rejects_non_admin(issuer, monkeypatch):
    jwt_issuer, key_source = issuer
    _patch_signing_key(monkeypatch, key_source.get_public_key_pem(), key_source.get_kid())

    verifier = JwtVerifier(jwks_url="https://fake/jwks.json", issuer="profile-service")
    app = _build_app_with_auth(verifier)
    client = TestClient(app)

    token, _ = jwt_issuer.issue_token(email="bob@sandvik.com", is_admin=False)
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    body = resp.json()
    # No install_error_handlers on this bare test app, so FastAPI's default HTTPException
    # shape ({"detail": {...}}) is expected here; the envelope shape is covered in
    # test_errors.py against an app that does install the handlers.
    assert body["detail"]["code"] == "FORBIDDEN"


def test_missing_token_rejected(issuer, monkeypatch):
    jwt_issuer, key_source = issuer
    _patch_signing_key(monkeypatch, key_source.get_public_key_pem(), key_source.get_kid())

    verifier = JwtVerifier(jwks_url="https://fake/jwks.json", issuer="profile-service")
    app = _build_app_with_auth(verifier)
    client = TestClient(app)

    resp = client.get("/me")
    assert resp.status_code == 401


def _fake_secret_client(secrets: dict[str, str]):
    fake_client = SimpleNamespace(
        get_secret=lambda name: SimpleNamespace(value=secrets.get(name))
    )
    return fake_client


def test_key_vault_key_source_reads_secrets(monkeypatch, tmp_path):
    from py_common.core.jwt_issue import KeyVaultKeySource

    local_source = LocalFileKeySource(tmp_path / "keys")
    secrets = {
        "priv": local_source.get_private_key_pem().decode("utf-8"),
        "pub": local_source.get_public_key_pem().decode("utf-8"),
        "kid": local_source.get_kid(),
    }
    monkeypatch.setattr(
        "py_common.core.jwt_issue.SecretClient",
        lambda vault_url, credential: _fake_secret_client(secrets),
    )
    monkeypatch.setattr("py_common.core.jwt_issue.DefaultAzureCredential", lambda: None)

    source = KeyVaultKeySource(
        key_vault_url="https://fake.vault.azure.net",
        private_key_secret_name="priv",
        public_key_secret_name="pub",
        kid_secret_name="kid",
    )
    assert source.get_private_key_pem() == local_source.get_private_key_pem()
    assert source.get_public_key_pem() == local_source.get_public_key_pem()
    assert source.get_kid() == local_source.get_kid()


def test_key_vault_key_source_raises_on_missing_secret(monkeypatch):
    from py_common.core.jwt_issue import KeyVaultKeySource

    monkeypatch.setattr(
        "py_common.core.jwt_issue.SecretClient",
        lambda vault_url, credential: _fake_secret_client({}),
    )
    monkeypatch.setattr("py_common.core.jwt_issue.DefaultAzureCredential", lambda: None)

    source = KeyVaultKeySource(
        key_vault_url="https://fake.vault.azure.net",
        private_key_secret_name="priv",
        public_key_secret_name="pub",
        kid_secret_name="kid",
    )
    with pytest.raises(RuntimeError):
        source.get_kid()


def test_key_vault_public_key_source_verifies_and_checks_kid(monkeypatch, tmp_path):
    from py_common.core.jwt_verify import KeyVaultPublicKeySource

    local_source = LocalFileKeySource(tmp_path / "keys")
    jwt_issuer = JwtIssuer(local_source, expiry_hours=8, issuer="profile-service")
    token, _ = jwt_issuer.issue_token(email="alice@sandvik.com", is_admin=False)

    secrets = {
        "pub": local_source.get_public_key_pem().decode("utf-8"),
        "kid": local_source.get_kid(),
    }
    monkeypatch.setattr(
        "py_common.core.jwt_verify.SecretClient",
        lambda vault_url, credential: _fake_secret_client(secrets),
    )
    monkeypatch.setattr("py_common.core.jwt_verify.DefaultAzureCredential", lambda: None)

    key_source = KeyVaultPublicKeySource(
        key_vault_url="https://fake.vault.azure.net",
        public_key_secret_name="pub",
        kid_secret_name="kid",
        cache_ttl_seconds=0,
    )
    signing_key = key_source.get_signing_key(token)
    claims = jwt.decode(token, signing_key, algorithms=["RS256"], issuer="profile-service")
    assert claims["sub"] == "alice@sandvik.com"

    secrets["kid"] = "some-other-kid"
    with pytest.raises(HTTPException):
        key_source.get_signing_key(token)
