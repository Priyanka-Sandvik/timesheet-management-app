"""Password hashing via Argon2id (argon2-cffi). Never log passwords or hashes."""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Returns an Argon2id hash string suitable for storage in PasswordHash."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Returns True iff `plain_password` matches `password_hash`. Never raises on mismatch."""
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False
    except Exception:
        return False
