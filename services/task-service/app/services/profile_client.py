"""httpx async client wrapping the (optional) email-existence validation call to Profile
Service used by POST /admin/tasks/{taskCode}/assign.

RECONCILED (see root README "Assumptions Made"): Profile Service's real, built contract
(architecture doc §8.1) has no per-email lookup route — only `GET /admin/users` (admin-only,
optional `activeOnly` query param), returning `{ users: [{ email, fullName, isActive, isAdmin,
createdAt, updatedAt }] }`. Since the assign endpoint is already admin-gated, forwarding the
caller's (admin's) Bearer JWT to that route is valid. This client fetches the full user list
and looks the target email up in-process (case-insensitive), treating:
  - found, isActive true or field absent -> valid
  - found, isActive false                -> invalid ("inactive")
  - not found in the list                -> invalid ("not found")
  - any error / network failure          -> fails OPEN (treated as valid) so Profile Service
    downtime does not block admin task assignment; a warning is logged in that case. Flip
    `fail_open=False` if the business wants fail-closed behavior instead.
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("task-service.profile_client")


class ProfileClientResult:
    def __init__(self, valid: bool, reason: str | None = None) -> None:
        self.valid = valid
        self.reason = reason


async def validate_user_exists(
    *,
    email: str,
    bearer_token: str | None,
    base_url: str,
    timeout_seconds: float = 5.0,
    fail_open: bool = True,
) -> ProfileClientResult:
    headers = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}
    url = f"{base_url.rstrip('/')}/admin/users"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("profile_client_unreachable", extra={"extra_fields": {"email": email, "error": str(exc)}})
        return ProfileClientResult(valid=fail_open, reason=None if fail_open else "Unable to reach Profile Service")

    if response.status_code >= 400:
        logger.warning(
            "profile_client_error_status",
            extra={"extra_fields": {"email": email, "status_code": response.status_code}},
        )
        return ProfileClientResult(
            valid=fail_open, reason=None if fail_open else f"Profile Service returned {response.status_code}"
        )

    try:
        body = response.json()
    except ValueError:
        body = {}

    users = body.get("users", []) if isinstance(body, dict) else []
    match = next((u for u in users if isinstance(u, dict) and u.get("email", "").lower() == email.lower()), None)

    if match is None:
        return ProfileClientResult(valid=False, reason="User not found in Profile Service")

    if match.get("isActive") is False:
        return ProfileClientResult(valid=False, reason="User is not active in Profile Service")

    return ProfileClientResult(valid=True)
