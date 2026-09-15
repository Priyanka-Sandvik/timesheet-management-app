"""Integration tests against a real Azurite Table Storage emulator.

Run with: pytest -m integration
If Azurite isn't reachable at the well-known local connection string, these tests skip
gracefully rather than failing the suite (no Azurite is expected to be running in CI for
this build).
"""
from __future__ import annotations

import pytest

AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)


def _azurite_reachable() -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", 10002), timeout=1.0):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture
async def azurite_table_client():
    if not _azurite_reachable():
        pytest.skip("Azurite is not reachable at 127.0.0.1:10002 - skipping integration test")

    from azure.data.tables.aio import TableServiceClient

    from py_common.core.table_client import ensure_table_exists_async

    service_client = TableServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    table_name = "TasksIntegrationTest"
    await ensure_table_exists_async(service_client, table_name)
    table_client = service_client.get_table_client(table_name)
    try:
        yield table_client
    finally:
        entities = [e async for e in table_client.list_entities()]
        for e in entities:
            await table_client.delete_entity(partition_key=e["PartitionKey"], row_key=e["RowKey"])
        await service_client.close()


@pytest.mark.asyncio
async def test_upsert_and_get_template_round_trip(azurite_table_client):
    from app.repositories.task_repository import TaskRepository

    repo = TaskRepository(azurite_table_client)
    await repo.upsert_template("ITEST1", {"TaskName": "Integration task", "Status": "Open", "Description": None, "Sponsor": None, "CostCentre": None, "CoEResponsible": None})

    fetched = await repo.get_template("ITEST1")
    assert fetched is not None
    assert fetched["TaskName"] == "Integration task"
    assert fetched["Status"] == "Open"


@pytest.mark.asyncio
async def test_assignment_partition_isolated_from_template(azurite_table_client):
    from app.repositories.task_repository import TaskRepository

    repo = TaskRepository(azurite_table_client)
    await repo.upsert_template("ITEST2", {"TaskName": "T", "Status": "Open", "Description": None, "Sponsor": None, "CostCentre": None, "CoEResponsible": None})
    await repo.upsert_assignment("someone@sandvik.com", "ITEST2", {"TaskName": "T", "Status": "Open", "Description": None, "Sponsor": None, "CostCentre": None, "CoEResponsible": None})

    my_rows = await repo.list_by_partition("someone@sandvik.com")
    assert len(my_rows) == 1
    assert my_rows[0]["RowKey"] == "ITEST2"

    template = await repo.get_template("ITEST2")
    assert template is not None
