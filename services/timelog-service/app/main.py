"""FastAPI application entrypoint for Timelog Service."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from py_common.core.errors import install_error_handlers
from py_common.core.table_client import ensure_table_exists_async, get_async_table_service_client

from app.config import get_settings
from app.core.logging import configure_logging
from app.repositories.timesheet_repository import TimesheetRepository
from app.routers import admin_export, timesheet
from app.services.profile_client import ProfileServiceClient
from app.services.task_client import TaskServiceClient
from app.services.timesheet_service import TimesheetService

settings = get_settings()
logger = configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    table_client = get_async_table_service_client(
        connection_string=settings.AZURE_STORAGE_CONNECTION_STRING or None,
    )
    await ensure_table_exists_async(table_client, settings.TIMESHEET_TABLE_NAME)

    repository = TimesheetRepository(table_client, settings.TIMESHEET_TABLE_NAME)
    task_client = TaskServiceClient(settings.TASK_SERVICE_BASE_URL)
    profile_client = ProfileServiceClient(settings.PROFILE_SERVICE_BASE_URL)
    timesheet_service = TimesheetService(repository, task_client)

    app.state.table_client = table_client
    app.state.timesheet_repository = repository
    app.state.task_client = task_client
    app.state.profile_client = profile_client
    app.state.timesheet_service = timesheet_service

    yield

    await table_client.close()


app = FastAPI(title="Timelog Service", version="1.0.0", lifespan=lifespan)

install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ALLOWED_ORIGIN] if settings.CORS_ALLOWED_ORIGIN else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(timesheet.router)
app.include_router(admin_export.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "timelog-service"}
