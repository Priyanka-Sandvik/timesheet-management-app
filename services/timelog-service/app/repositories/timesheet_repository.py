"""Table Storage access layer for the Timesheet table (async client, per FastAPI async
endpoints).

PartitionKey = UserId (Email). RowKey = `EntryDate_TaskCode`.
All queries here are partition-scoped (PartitionKey == a specific user's email) — never a
cross-partition/full-table scan.
"""
from __future__ import annotations

from datetime import date

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import UpdateMode
from azure.data.tables.aio import TableServiceClient as AsyncTableServiceClient

from app.models.entities import TimesheetEntity, make_row_key


class TimesheetRepository:
    def __init__(self, table_client: AsyncTableServiceClient, table_name: str) -> None:
        self._table_name = table_name
        self._table_client = table_client.get_table_client(table_name)

    async def get_week_entries(self, user_id: str, week_start: date, week_end: date) -> list[TimesheetEntity]:
        """Partition-scoped range query for a single user's rows within [week_start, week_end]."""
        lower = f"{week_start.isoformat()}_"
        upper = f"{week_end.isoformat()}_￿"
        query_filter = (
            f"PartitionKey eq '{_escape(user_id)}' and RowKey ge '{lower}' and RowKey le '{upper}'"
        )
        results: list[TimesheetEntity] = []
        async for entity in self._table_client.query_entities(query_filter):
            results.append(TimesheetEntity.from_table_entity(entity))
        return results

    async def get_month_entries(self, user_id: str, lower_bound: str, upper_bound: str) -> list[TimesheetEntity]:
        """Partition-scoped RowKey range query: RowKey >= lower_bound and RowKey < upper_bound.

        `lower_bound`/`upper_bound` are e.g. "2026-08-01_" and "2026-09-01_" — lexicographic
        comparison over ISO date prefixes works correctly for month boundaries.
        """
        query_filter = (
            f"PartitionKey eq '{_escape(user_id)}' and RowKey ge '{lower_bound}' and RowKey lt '{upper_bound}'"
        )
        results: list[TimesheetEntity] = []
        async for entity in self._table_client.query_entities(query_filter):
            results.append(TimesheetEntity.from_table_entity(entity))
        return results

    async def get_entry(self, user_id: str, entry_date: date, task_code: str) -> TimesheetEntity | None:
        row_key = make_row_key(entry_date, task_code)
        try:
            entity = await self._table_client.get_entity(partition_key=user_id, row_key=row_key)
        except ResourceNotFoundError:
            return None
        return TimesheetEntity.from_table_entity(entity)

    async def upsert_entry(self, entity: TimesheetEntity) -> None:
        await self._table_client.upsert_entity(entity.to_table_entity(), mode=UpdateMode.MERGE)

    async def upsert_entries(self, entities: list[TimesheetEntity]) -> None:
        for entity in entities:
            await self.upsert_entry(entity)


def _escape(value: str) -> str:
    """Escapes single quotes for OData filter string literals."""
    return value.replace("'", "''")
