import shutil
import tempfile
from pathlib import Path

import jwt
import pytest
from py_common.core.jwt_issue import JwtIssuer, LocalFileKeySource


@pytest.fixture
def issuer():
    tmp_dir = tempfile.mkdtemp()
    try:
        key_source = LocalFileKeySource(tmp_dir)
        yield JwtIssuer(key_source=key_source, expiry_hours=8, issuer="profile-service")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_issue_token_contains_expected_claims(issuer):
    token, expires_in = issuer.issue_token(email="alice@sandvik.com", is_admin=True, full_name="Alice Example")

    assert expires_in == 8 * 3600

    public_key_pem = issuer._key_source.get_public_key_pem()  # test-only introspection
    claims = jwt.decode(token, public_key_pem, algorithms=["RS256"], issuer="profile-service")

    assert claims["sub"] == "alice@sandvik.com"
    assert claims["isAdmin"] is True
    assert claims["fullName"] == "Alice Example"
    assert claims["iss"] == "profile-service"
    assert "exp" in claims and "iat" in claims


def test_issue_token_non_admin(issuer):
    token, _ = issuer.issue_token(email="bob@sandvik.com", is_admin=False)
    public_key_pem = issuer._key_source.get_public_key_pem()
    claims = jwt.decode(token, public_key_pem, algorithms=["RS256"], issuer="profile-service")
    assert claims["isAdmin"] is False
    assert "fullName" not in claims


def test_get_jwks_returns_public_key_document(issuer):
    jwks = issuer.get_jwks()
    assert "keys" in jwks
    assert len(jwks["keys"]) == 1
    key = jwks["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert "n" in key and "e" in key
