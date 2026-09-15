"""Central configuration for Task Service, loaded from environment variables / .env.

All names here match architecture doc §11 exactly, plus a small set of additional
local-dev-only / behavior-tuning vars documented in .env.example.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Azure Table Storage ---
    AZURE_STORAGE_ACCOUNT_URL: str = ""
    TASKS_TABLE_NAME: str = "Tasks"
    ENVIRONMENT: str = "local"
    AZURE_STORAGE_CONNECTION_STRING: str = ""

    # --- Profile Service integration ---
    PROFILE_SERVICE_BASE_URL: str = "http://localhost:8001"

    # --- JWT verification (Task Service verifies tokens issued by Profile Service) ---
    JWKS_URL: str = "http://localhost:8001/.well-known/jwks.json"
    JWT_ISSUER: str = "profile-service"

    # --- CORS ---
    CORS_ALLOWED_ORIGIN: str = "https://localhost"

    # --- Networking ---
    PORT: int = 8002

    # --- Behavior tuning (not in architecture doc §11 env var table; local defaults) ---
    # Whether POST /admin/tasks/{taskCode}/assign validates each email against Profile
    # Service before assigning. See app/services/profile_client.py.
    VALIDATE_ASSIGN_EMAILS_WITH_PROFILE_SERVICE: bool = True
    PROFILE_SERVICE_TIMEOUT_SECONDS: float = 5.0
    DEFAULT_ADMIN_LIST_PAGE_SIZE: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
