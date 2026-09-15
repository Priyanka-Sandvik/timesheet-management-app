"""Task Service FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from py_common.core.errors import install_error_handlers
from py_common.core.table_client import ensure_table_exists_async, get_async_table_service_client

from app.config import get_settings
from app.core.logging import setup_logging
from app.routers import admin_tasks, tasks

settings = get_settings()
logger = setup_logging("task-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    table_service_client = get_async_table_service_client(
        environment=settings.ENVIRONMENT,
        account_url=settings.AZURE_STORAGE_ACCOUNT_URL or None,
        connection_string=settings.AZURE_STORAGE_CONNECTION_STRING or None,
    )
    await ensure_table_exists_async(table_service_client, settings.TASKS_TABLE_NAME)
    app.state.table_service_client = table_service_client
    app.state.table_client = table_service_client.get_table_client(settings.TASKS_TABLE_NAME)
    try:
        yield
    finally:
        await table_service_client.close()


app = FastAPI(title="Task Service", version="1.0.0", lifespan=lifespan)

install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_ORIGIN] if settings.CORS_ALLOWED_ORIGIN else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(admin_tasks.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "task-service"}
