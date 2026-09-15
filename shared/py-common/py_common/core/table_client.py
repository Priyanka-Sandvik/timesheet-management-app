"""Azure Table Storage client factory.

Production/Azure: uses `DefaultAzureCredential` (system-assigned Managed Identity) against
`AZURE_STORAGE_ACCOUNT_URL`.

Local dev (Azurite): connection-string auth is used ONLY when `ENVIRONMENT=local`. Any other
ENVIRONMENT value with a missing account URL is a hard configuration error, not a silent
fallback.
"""
from __future__ import annotations

from azure.data.tables import TableServiceClient
from azure.data.tables.aio import TableServiceClient as AsyncTableServiceClient

_LOCAL_ENVIRONMENT_VALUE = "local"


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required configuration: {name}")
    return value


def get_table_service_client(
    *,
    environment: str,
    account_url: str | None = None,
    connection_string: str | None = None,
) -> TableServiceClient:
    """Synchronous Table Storage client factory.

    - `environment == "local"`: requires `connection_string` (e.g. Azurite's well-known
      connection string). This is the ONLY path allowed to use a connection string.
    - any other environment: requires `account_url` and uses `DefaultAzureCredential`.
    """
    if environment == _LOCAL_ENVIRONMENT_VALUE:
        cs = _require(connection_string, "AZURE_STORAGE_CONNECTION_STRING (required when ENVIRONMENT=local)")
        return TableServiceClient.from_connection_string(cs)

    from azure.identity import DefaultAzureCredential

    url = _require(account_url, "AZURE_STORAGE_ACCOUNT_URL")
    return TableServiceClient(endpoint=url, credential=DefaultAzureCredential())


def get_async_table_service_client(
    *,
    environment: str,
    account_url: str | None = None,
    connection_string: str | None = None,
) -> AsyncTableServiceClient:
    """Async variant of `get_table_service_client`, for use in async FastAPI repositories."""
    if environment == _LOCAL_ENVIRONMENT_VALUE:
        cs = _require(connection_string, "AZURE_STORAGE_CONNECTION_STRING (required when ENVIRONMENT=local)")
        return AsyncTableServiceClient.from_connection_string(cs)

    from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

    url = _require(account_url, "AZURE_STORAGE_ACCOUNT_URL")
    return AsyncTableServiceClient(endpoint=url, credential=AsyncDefaultAzureCredential())


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
