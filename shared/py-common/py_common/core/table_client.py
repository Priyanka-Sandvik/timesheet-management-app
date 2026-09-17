"""Azure Table Storage client factory.

Always authenticates via `AZURE_STORAGE_CONNECTION_STRING`, in every environment including
production. There is no Managed Identity / account-URL path.
"""
from __future__ import annotations

from azure.data.tables import TableServiceClient
from azure.data.tables.aio import TableServiceClient as AsyncTableServiceClient


def _require_connection_string(connection_string: str | None) -> str:
    if not connection_string:
        raise RuntimeError("Missing required configuration: AZURE_STORAGE_CONNECTION_STRING")
    return connection_string


def get_table_service_client(*, connection_string: str | None) -> TableServiceClient:
    """Synchronous Table Storage client factory."""
    cs = _require_connection_string(connection_string)
    return TableServiceClient.from_connection_string(cs)


def get_async_table_service_client(*, connection_string: str | None) -> AsyncTableServiceClient:
    """Async variant of `get_table_service_client`, for use in async FastAPI repositories."""
    cs = _require_connection_string(connection_string)
    return AsyncTableServiceClient.from_connection_string(cs)


def ensure_table_exists(client: TableServiceClient, table_name: str) -> None:
    """Idempotently creates a table if it doesn't already exist. Safe to call at startup."""
    try:
        client.create_table(table_name)
    except Exception as exc:  # azure.core.exceptions.ResourceExistsError
        if "TableAlreadyExists" not in str(exc) and "already exists" not in str(exc).lower():
            raise


async def ensure_table_exists_async(client: AsyncTableServiceClient, table_name: str) -> None:
    try:
        await client.create_table(table_name)
    except Exception as exc:
        if "TableAlreadyExists" not in str(exc) and "already exists" not in str(exc).lower():
            raise
