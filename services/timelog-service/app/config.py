"""Central configuration for Timelog Service, loaded from environment variables / .env.

All names here match architecture doc §11 exactly, plus a small set of additional
local-dev-only vars documented in .env.example.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Azure Table Storage ---
    TIMESHEET_TABLE_NAME: str = "Timesheet"
    AZURE_STORAGE_CONNECTION_STRING: str = ""

    # --- Upstream services ---
    TASK_SERVICE_BASE_URL: str = "http://localhost:8002"
    PROFILE_SERVICE_BASE_URL: str = "http://localhost:8001"

    # --- Auth ---
    USE_LOCAL_KEY: bool = True
    JWKS_URL: str = "http://localhost:8001/.well-known/jwks.json"

    # --- JWT verification key source, production only (USE_LOCAL_KEY=false) ---
    KEY_VAULT_URL: str = ""
    JWT_PUBLIC_KEY_SECRET_NAME: str = "jwt-signing-public-key"
    JWT_KID_SECRET_NAME: str = "jwt-signing-kid"

    # --- CORS ---
    CORS_ALLOWED_ORIGIN: str = "https://localhost"

    # --- Networking ---
    PORT: int = 8003


@lru_cache
def get_settings() -> Settings:
    return Settings()
