"""RS256 JWT issuance helper — used only by Profile Service.

Supports two key-source strategies behind a common `KeySource` interface:
- `LocalFileKeySource`: generates (once) / loads an RSA keypair from local disk.
  Activated via `USE_LOCAL_KEY=true` for local dev and tests.
- `KeyVaultKeySource`: stub for reading the private key from Azure Key Vault via
  Managed Identity. NOT IMPLEMENTED YET — raises NotImplementedError. Swapping
  this in for real Key Vault support later is a one-line change in
  `services/profile-service/app/core/jwt.py` (construct `KeyVaultKeySource` instead
  of `LocalFileKeySource` based on `USE_LOCAL_KEY`).
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey


class KeySource(ABC):
    """Abstraction over "where the RS256 signing key comes from".

    Concrete implementations must provide the PEM-encoded private key, the PEM-encoded
    public key, and a stable key id (`kid`) used in the JWKS document and the JWT header.
    """

    @abstractmethod
    def get_private_key_pem(self) -> bytes: ...

    @abstractmethod
    def get_public_key_pem(self) -> bytes: ...

    @abstractmethod
    def get_kid(self) -> str: ...


class LocalFileKeySource(KeySource):
    """Generates (once) and/or loads a local RSA keypair from disk.

    Used for local dev / tests / any deployment where `USE_LOCAL_KEY=true`.
    Never use this in production against real Azure infra.
    """

    def __init__(self, key_dir: str | Path, key_size: int = 2048) -> None:
        self._key_dir = Path(key_dir)
        self._key_dir.mkdir(parents=True, exist_ok=True)
        self._private_path = self._key_dir / "jwt_private_key.pem"
        self._public_path = self._key_dir / "jwt_public_key.pem"
        self._kid_path = self._key_dir / "jwt_kid.txt"
        self._key_size = key_size
        self._ensure_keys_exist()

    def _ensure_keys_exist(self) -> None:
        if self._private_path.exists() and self._public_path.exists() and self._kid_path.exists():
            return
        private_key: RSAPrivateKey = rsa.generate_private_key(public_exponent=65537, key_size=self._key_size)
        public_key: RSAPublicKey = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self._private_path.write_bytes(private_pem)
        self._public_path.write_bytes(public_pem)
        self._kid_path.write_text(uuid.uuid4().hex)

    def get_private_key_pem(self) -> bytes:
        return self._private_path.read_bytes()

    def get_public_key_pem(self) -> bytes:
        return self._public_path.read_bytes()

    def get_kid(self) -> str:
        return self._kid_path.read_text().strip()


class KeyVaultKeySource(KeySource):
    """Stub for reading the JWT signing key from Azure Key Vault via Managed Identity.

    TODO(prod): Implement using `azure.identity.DefaultAzureCredential` +
    `azure.keyvault.secrets.SecretClient` (or `azure.keyvault.keys.KeyClient` if using a
    Key Vault Key rather than a Secret) to fetch the RSA private key referenced by
    `KEY_VAULT_URL` / `JWT_KEY_NAME` (see architecture doc §11). Cache the material in
    memory with a short TTL. Until implemented, deployments must set `USE_LOCAL_KEY=true`
    and use `LocalFileKeySource` instead.
    """

    def __init__(self, key_vault_url: str, key_name: str) -> None:
        self._key_vault_url = key_vault_url
        self._key_name = key_name

    def get_private_key_pem(self) -> bytes:
        raise NotImplementedError(
            "KeyVaultKeySource is not implemented yet. Set USE_LOCAL_KEY=true to use "
            "LocalFileKeySource for now. TODO(prod): fetch signing key from Azure Key Vault "
            "via DefaultAzureCredential."
        )

    def get_public_key_pem(self) -> bytes:
        raise NotImplementedError(
            "KeyVaultKeySource is not implemented yet. Set USE_LOCAL_KEY=true to use "
            "LocalFileKeySource for now."
        )

    def get_kid(self) -> str:
        raise NotImplementedError(
            "KeyVaultKeySource is not implemented yet. Set USE_LOCAL_KEY=true to use "
            "LocalFileKeySource for now."
        )


class JwtIssuer:
    """Issues RS256 JWTs using the private key from a `KeySource`."""

    def __init__(self, key_source: KeySource, expiry_hours: int = 8, issuer: str = "profile-service") -> None:
        self._key_source = key_source
        self._expiry_hours = expiry_hours
        self._issuer = issuer

    def issue_token(self, *, email: str, is_admin: bool, full_name: str | None = None) -> tuple[str, int]:
        """Returns (access_token, expires_in_seconds)."""
        now = int(time.time())
        expires_in = self._expiry_hours * 3600
        payload = {
            "sub": email,
            "isAdmin": is_admin,
            "iat": now,
            "exp": now + expires_in,
            "iss": self._issuer,
        }
        if full_name is not None:
            payload["fullName"] = full_name
        headers = {"kid": self._key_source.get_kid()}
        token = jwt.encode(payload, self._key_source.get_private_key_pem(), algorithm="RS256", headers=headers)
        return token, expires_in

    def get_jwks(self) -> dict:
        """Build a JWKS document (public key only) per RFC 7517."""
        public_key = serialization.load_pem_public_key(self._key_source.get_public_key_pem())
        numbers = public_key.public_numbers()  # type: ignore[union-attr]
        n = _int_to_base64url(numbers.n)
        e = _int_to_base64url(numbers.e)
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self._key_source.get_kid(),
                    "n": n,
                    "e": e,
                }
            ]
        }


def _int_to_base64url(value: int) -> str:
    import base64

    byte_length = (value.bit_length() + 7) // 8
    value_bytes = value.to_bytes(byte_length, "big")
    return base64.urlsafe_b64encode(value_bytes).rstrip(b"=").decode("ascii")
