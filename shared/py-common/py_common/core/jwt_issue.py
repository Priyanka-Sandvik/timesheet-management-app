"""RS256 JWT issuance helper — used only by Profile Service.

Supports two key-source strategies behind a common `KeySource` interface:
- `LocalFileKeySource`: generates (once) / loads an RSA keypair from local disk.
  Activated via `USE_LOCAL_KEY=true` for local dev and tests.
- `KeyVaultKeySource`: reads the private key, public key, and kid from Azure Key Vault
  secrets via Managed Identity (`DefaultAzureCredential`). Used in production
  (`USE_LOCAL_KEY=false`).
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import jwt
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
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
    """Reads the JWT signing private key, public key, and kid from Azure Key Vault secrets.

    Authenticates via `DefaultAzureCredential`, which resolves to the Container App's
    system-assigned Managed Identity in Azure and to `az login` / env-var credentials
    locally. Each secret is expected to hold its value as plain text (PEM for the two key
    secrets, the raw kid string for the kid secret) and is cached in memory for
    `cache_ttl_seconds` to avoid a Key Vault round-trip on every token issuance.
    """

    def __init__(
        self,
        key_vault_url: str,
        private_key_secret_name: str,
        public_key_secret_name: str,
        kid_secret_name: str,
        cache_ttl_seconds: int = 300,
    ) -> None:
        self._private_key_secret_name = private_key_secret_name
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
        value = self._client.get_secret(name).value
        if not value:
            raise RuntimeError(f"Key Vault secret '{name}' is missing or empty")
        self._cache[name] = (now, value)
        return value

    def get_private_key_pem(self) -> bytes:
        return self._get_secret(self._private_key_secret_name).encode("utf-8")

    def get_public_key_pem(self) -> bytes:
        return self._get_secret(self._public_key_secret_name).encode("utf-8")

    def get_kid(self) -> str:
        return self._get_secret(self._kid_secret_name)


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
