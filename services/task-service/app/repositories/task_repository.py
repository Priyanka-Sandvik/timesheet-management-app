"""Table Storage access for the Tasks table (architecture doc §6).

PartitionKey = AssignedUserId (email) or the literal string "UNASSIGNED" (template rows).
RowKey = TaskCode.

This module owns ALL entity <-> pydantic mapping and partition-scoped querying. No
business rules live here (see app/services/task_service.py) - just storage access.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables.aio import TableClient

from app.models.schemas import UNASSIGNED_PARTITION, TaskOut

_UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime(_UTC_FMT)


def entity_to_task_out(entity: dict[str, Any]) -> TaskOut:
    partition_key = entity["PartitionKey"]
    return TaskOut(
        taskCode=entity["RowKey"],
        taskName=entity.get("TaskName", ""),
        description=entity.get("Description") or None,
        sponsor=entity.get("Sponsor") or None,
        costCentre=entity.get("CostCentre") or None,
        coeResponsible=entity.get("CoEResponsible") or None,
        status=entity.get("Status", "Open"),
        assignedUserId=None if partition_key == UNASSIGNED_PARTITION else partition_key,
        createdAt=entity.get("CreatedAt"),
        updatedAt=entity.get("UpdatedAt"),
    )


class TaskRepository:
    def __init__(self, table_client: TableClient) -> None:
        self._table = table_client

    # ------------------------------------------------------------------ #
    # Template (UNASSIGNED) rows
    # ------------------------------------------------------------------ #
    async def get_template(self, task_code: str) -> dict[str, Any] | None:
        return await self._get(UNASSIGNED_PARTITION, task_code)

    async def upsert_template(self, task_code: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._upsert(UNASSIGNED_PARTITION, task_code, fields)

    async def delete_template(self, task_code: str) -> bool:
        return await self._delete(UNASSIGNED_PARTITION, task_code)

    # ------------------------------------------------------------------ #
    # Per-employee assignment rows
    # ------------------------------------------------------------------ #
    async def get_assignment(self, email: str, task_code: str) -> dict[str, Any] | None:
        return await self._get(email, task_code)

    async def upsert_assignment(self, email: str, task_code: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._upsert(email, task_code, fields)

    async def delete_assignment(self, email: str, task_code: str) -> bool:
        return await self._delete(email, task_code)

    async def list_by_partition(self, partition_key: str) -> list[dict[str, Any]]:
        results = []
        query_filter = "PartitionKey eq @pk"
        async for entity in self._table.query_entities(query_filter, parameters={"pk": partition_key}):
            results.append(dict(entity))
        return results

    async def list_all(
        self, page_size: int, continuation_token: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        pages = self._table.list_entities(results_per_page=page_size).by_page(
            continuation_token=continuation_token
        )
        try:
            page = await pages.__anext__()
        except StopAsyncIteration:
            return [], None
        items = [dict(entity) async for entity in page]
        next_token = pages.continuation_token
        return items, (next_token or None)

    async def list_all_unpaged(self, status: str | None = None) -> list[dict[str, Any]]:
        """Fetches every row in the table (all partitions), optionally pushing an exact
        `Status` match down to the OData query. Used when a text search filter is also
        active, since Table Storage has no substring/contains operator to push that part
        down - see TaskService._list_all_tasks_filtered for why pagination then has to be
        done in-memory over this full result set.
        """
        results: list[dict[str, Any]] = []
        if status:
            query_filter = "Status eq @status"
            async for entity in self._table.query_entities(query_filter, parameters={"status": status}):
                results.append(dict(entity))
        else:
            async for entity in self._table.list_entities():
                results.append(dict(entity))
        return results

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    async def _get(self, partition_key: str, row_key: str) -> dict[str, Any] | None:
        try:
            entity = await self._table.get_entity(partition_key=partition_key, row_key=row_key)
        except ResourceNotFoundError:
            return None
        return dict(entity)

    async def _upsert(self, partition_key: str, row_key: str, fields: dict[str, Any]) -> dict[str, Any]:
        existing = await self._get(partition_key, row_key)
        now = _now()
        entity: dict[str, Any] = {
            "PartitionKey": partition_key,
            "RowKey": row_key,
            "CreatedAt": existing["CreatedAt"] if existing and existing.get("CreatedAt") else now,
            "UpdatedAt": now,
        }
        entity.update(fields)
        await self._table.upsert_entity(entity, mode="merge" if existing else "replace")
        return entity

    async def _delete(self, partition_key: str, row_key: str) -> bool:
        try:
            await self._table.delete_entity(partition_key=partition_key, row_key=row_key)
        except ResourceNotFoundError:
            return False
        return True
