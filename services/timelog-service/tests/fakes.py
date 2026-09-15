"""In-memory fakes used across unit tests — no network, no Azurite."""
from __future__ import annotations

from datetime import date

from app.models.entities import TimesheetEntity, make_row_key
from app.services.task_client import TaskAssignment


class FakeTimesheetRepository:
    """In-memory stand-in for TimesheetRepository, keyed like the real table
    (PartitionKey=user_id, RowKey=EntryDate_TaskCode).
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], TimesheetEntity] = {}

    async def get_week_entries(self, user_id: str, week_start: date, week_end: date) -> list[TimesheetEntity]:
        return [
            e
            for (pk, _rk), e in self._store.items()
            if pk == user_id and week_start <= e.entry_date <= week_end
        ]

    async def get_month_entries(self, user_id: str, lower_bound: str, upper_bound: str) -> list[TimesheetEntity]:
        return [
            e
            for (pk, rk), e in self._store.items()
            if pk == user_id and lower_bound <= rk < upper_bound
        ]

    async def get_entry(self, user_id: str, entry_date: date, task_code: str) -> TimesheetEntity | None:
        return self._store.get((user_id, make_row_key(entry_date, task_code)))

    async def upsert_entry(self, entity: TimesheetEntity) -> None:
        self._store[(entity.user_id, entity.row_key)] = entity

    async def upsert_entries(self, entities: list[TimesheetEntity]) -> None:
        for e in entities:
            await self.upsert_entry(e)

    def all_entries(self) -> list[TimesheetEntity]:
        return list(self._store.values())


class FakeTaskServiceClient:
    def __init__(self, assignments: list[dict]) -> None:
        self._assignments = [TaskAssignment(a) for a in assignments]

    async def get_my_tasks(self, bearer_token: str) -> list[TaskAssignment]:
        return list(self._assignments)
