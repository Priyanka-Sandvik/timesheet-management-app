"""Unit tests for TaskServiceClient response parsing edge cases.

Tests that the client correctly handles various response formats from the Task Service,
including malformed or unexpected responses.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from py_common.core.errors import AppError

from app.services.task_client import TaskServiceClient, TaskAssignment


@pytest.mark.asyncio
async def test_task_client_parses_correct_format() -> None:
    """Test that the client correctly parses a properly-formatted response."""
    client = TaskServiceClient("http://localhost:8002")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tasks": [
            {"taskCode": "TASK-A", "taskName": "Task A", "projectName": "Project X"},
            {"taskCode": "TASK-B", "taskName": "Task B", "projectName": "Project Y"},
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await client.get_my_tasks("token")

        assert len(result) == 2
        assert result[0].task_code == "TASK-A"
        assert result[0].task_name == "Task A"
        assert result[1].task_code == "TASK-B"


@pytest.mark.asyncio
async def test_task_client_handles_missing_tasks_key() -> None:
    """Test that the client gracefully handles a response without a 'tasks' key."""
    client = TaskServiceClient("http://localhost:8002")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"error": "unexpected format"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await client.get_my_tasks("token")

        # Should return an empty list, not try to iterate over dict keys
        assert result == []


@pytest.mark.asyncio
async def test_task_client_handles_list_format() -> None:
    """Test that the client correctly handles a list response format."""
    client = TaskServiceClient("http://localhost:8002")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"taskCode": "TASK-A", "taskName": "Task A", "projectName": "Project X"},
    ]

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await client.get_my_tasks("token")

        assert len(result) == 1
        assert result[0].task_code == "TASK-A"


@pytest.mark.asyncio
async def test_task_client_rejects_tasks_not_as_list() -> None:
    """Test that the client rejects when 'tasks' field is not a list."""
    client = TaskServiceClient("http://localhost:8002")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tasks": "not a list"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        with pytest.raises(AppError) as exc_info:
            await client.get_my_tasks("token")

        assert exc_info.value.status_code == 502
        assert "tasks field is not a list" in exc_info.value.message


@pytest.mark.asyncio
async def test_task_client_handles_empty_list() -> None:
    """Test that the client correctly handles an empty list response."""
    client = TaskServiceClient("http://localhost:8002")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tasks": []}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await client.get_my_tasks("token")

        assert result == []


@pytest.mark.asyncio
async def test_task_client_handles_null_response() -> None:
    """Test that the client gracefully handles a null response."""
    client = TaskServiceClient("http://localhost:8002")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = None

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = await client.get_my_tasks("token")

        # Should return an empty list for unexpected types
        assert result == []
