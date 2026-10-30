"""Central configuration for Profile Service, loaded from environment variables / .env.

All names here match architecture doc §11 exactly, plus a small set of additional
local-dev-only vars documented in .env.example.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Azure Table Storage ---
    USERS_TABLE_NAME: str = "Users"
    AZURE_STORAGE_CONNECTION_STRING: str = ""

    # --- JWT signing key source ---
    KEY_VAULT_URL: str = ""
    JWT_PRIVATE_KEY_SECRET_NAME: str = "jwt-private-key"
    JWT_PUBLIC_KEY_SECRET_NAME: str = "jwt-public-key"
    JWT_KID_SECRET_NAME: str = "jwt-kid"
    JWT_EXPIRY_HOURS: int = 8
    USE_LOCAL_KEY: bool = True
    LOCAL_KEY_DIR: str = "./.keys"

    # --- Auth / business rules ---
    # Admin accounts: semicolon-separated emails (a legacy ":password" suffix is ignored).
    # Admins register through /auth/register like any employee and use that one password;
    # being listed here only grants the isAdmin claim on login.
    ADMIN_CREDENTIALS: str = ""
    ALLOWED_EMAIL_DOMAIN: str = "sandvik.com"

    # --- CORS ---
    CORS_ALLOWED_ORIGIN: str = "https://localhost"

    # --- Rate limiting ---
    AUTH_RATE_LIMIT_PER_MINUTE: int = 20

    # --- Networking ---
    PORT: int = 8001
    JWKS_URL: str = "http://localhost:8001/.well-known/jwks.json"

    JWT_ISSUER: str = "profile-service"

    @property
    def admin_emails(self) -> set[str]:
        """Lower-cased admin emails parsed from ADMIN_CREDENTIALS.

        Format: "email1;email2". Entries are semicolon-separated. A legacy ":password" suffix
        is accepted but ignored: admins use the single password they registered with.
        """
        result: set[str] = set()
        for entry in self.ADMIN_CREDENTIALS.split(";"):
            email = entry.partition(":")[0].strip().lower()
            if email:
                result.add(email)
        return result


@lru_cache
def get_settings() -> Settings:
    return Settings()
