"""Async HTTP client for Profile Service, forwarding the caller's Bearer JWT unchanged."""
from __future__ import annotations

import httpx
from py_common.core.errors import AppError


class ProfileServiceClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def get_active_users(self, bearer_token: str) -> list[dict]:
        """GET /admin/users?activeOnly=true — returns the list of active employees."""
        url = f"{self._base_url}/admin/users"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params={"activeOnly": "true"}, headers=headers)
        except httpx.HTTPError as exc:
            raise AppError(
                status_code=502,
                code="UPSTREAM_ERROR",
                message=f"Unable to reach Profile Service: {exc}",
            ) from exc

        if response.status_code >= 400:
            raise AppError(
                status_code=502,
                code="UPSTREAM_ERROR",
                message=f"Profile Service returned {response.status_code} for /admin/users",
            )

        payload = response.json()
        users = payload.get("users", payload) if isinstance(payload, dict) else payload
        return list(users)
