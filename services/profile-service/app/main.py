"""Profile Service FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from py_common.core.errors import install_error_handlers
from py_common.core.table_client import ensure_table_exists

from app.config import get_settings
from app.core.logging import configure_logging, log_event
from app.dependencies import get_table_service_client_singleton
from app.routers import admin, auth, me

logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    service_client = get_table_service_client_singleton()
    ensure_table_exists(service_client, settings.USERS_TABLE_NAME)
    log_event(logger, "startup", service="profile-service", table=settings.USERS_TABLE_NAME)
    yield
    log_event(logger, "shutdown", service="profile-service")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Profile Service", version="1.0.0", lifespan=lifespan)

    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.CORS_ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(me.router)
    app.include_router(admin.router)

    return app


app = create_app()
