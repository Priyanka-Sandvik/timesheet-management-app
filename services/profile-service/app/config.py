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
    ADMIN_EMAILS: str = ""
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
    def admin_emails_set(self) -> set[str]:
        """Case-insensitive set of admin emails parsed from the comma-separated env var."""
        return {e.strip().lower() for e in self.ADMIN_EMAILS.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
