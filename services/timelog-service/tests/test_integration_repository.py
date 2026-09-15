"""Integration tests against a real Azurite Table Storage emulator.

Skips gracefully (never hard-fails) if Azurite is not reachable at the well-known local
connection string / port 10002 (Table service).
"""
from __future__ import annotations

import socket
from datetime import date, datetime, timezone

import pytest

AZURITE_TABLE_HOST = "127.0.0.1"
AZURITE_TABLE_PORT = 10002

AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)


def _azurite_reachable() -> bool:
    try:
        with socket.create_connection((AZURITE_TABLE_HOST, AZURITE_TABLE_PORT), timeout=1.0):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture
async def repository():
    if not _azurite_reachable():
        pytest.skip("Azurite is not reachable on 127.0.0.1:10002 — skipping integration test")

    from azure.data.tables.aio import TableServiceClient as AsyncTableServiceClient

    from app.repositories.timesheet_repository import TimesheetRepository

    table_name = "TimesheetIntegrationTest"
    client = AsyncTableServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    try:
        await client.create_table(table_name)
    except Exception:
        pass

    repo = TimesheetRepository(client, table_name)
    yield repo

    table_client = client.get_table_client(table_name)
    async for entity in table_client.list_entities():
        await table_client.delete_entity(entity["PartitionKey"], entity["RowKey"])
    await client.close()


@pytest.mark.asyncio
async def test_upsert_and_get_week_entries_round_trip(repository) -> None:
    from app.models.entities import TimesheetEntity

    now = datetime.now(timezone.utc)
    entity = TimesheetEntity(
        user_id="integration-test@sandvik.com",
        entry_date=date(2026, 8, 3),
        task_code="TASK-INT-1",
        task_name="Integration Task",
        project_name="Integration Project",
        week_start_date=date(2026, 8, 3),
        hours_logged=3.5,
        notes="integration test entry",
        status="Pending",
        created_at=now,
        updated_at=now,
    )

    await repository.upsert_entry(entity)

    results = await repository.get_week_entries(
        "integration-test@sandvik.com", date(2026, 8, 3), date(2026, 8, 9)
    )
    assert len(results) == 1
    assert results[0].task_code == "TASK-INT-1"
    assert results[0].hours_logged == 3.5


@pytest.mark.asyncio
async def test_month_range_query_is_partition_scoped(repository) -> None:
    from app.models.entities import TimesheetEntity

    now = datetime.now(timezone.utc)
    in_month = TimesheetEntity(
        user_id="integration-test-2@sandvik.com",
        entry_date=date(2026, 8, 15),
        task_code="TASK-A",
        task_name="A",
        project_name="P",
        week_start_date=date(2026, 8, 10),
        hours_logged=2.0,
        notes=None,
        status="Pending",
        created_at=now,
        updated_at=now,
    )
    out_of_month = TimesheetEntity(
        user_id="integration-test-2@sandvik.com",
        entry_date=date(2026, 9, 1),
        task_code="TASK-A",
        task_name="A",
        project_name="P",
        week_start_date=date(2026, 8, 31),
        hours_logged=5.0,
        notes=None,
        status="Pending",
        created_at=now,
        updated_at=now,
    )
    await repository.upsert_entries([in_month, out_of_month])

    results = await repository.get_month_entries(
        "integration-test-2@sandvik.com", "2026-08-01_", "2026-09-01_"
    )
    assert len(results) == 1
    assert results[0].entry_date == date(2026, 8, 15)
