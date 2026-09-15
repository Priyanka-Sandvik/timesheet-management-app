"""Standard error envelope (architecture doc §8.4) + installable FastAPI exception handlers.

Envelope shape (exact):
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable summary",
    "details": [ { "field": "hours", "issue": "must be between 0 and 24" } ]
  }
}
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """Raise this from Service/Repository layers to produce a standard error envelope response.

    Routers/services should prefer raising this (or HTTPException) over ad-hoc dict responses.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)


def _envelope(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict:
    return ErrorEnvelope(
        error=ErrorBody(code=code, message=message, details=[ErrorDetail(**d) for d in (details or [])])
    ).model_dump()


# Maps common HTTP status codes to a default error `code` string when the raiser
# (e.g. bare HTTPException) didn't already provide a structured envelope.
_STATUS_CODE_DEFAULTS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
}


def install_error_handlers(app: FastAPI) -> None:
    """Register exception handlers on `app` so every error response (across all 3 services)
    uses the standard error envelope shape from architecture doc §8.4.
    """

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Map FastAPI's default 422 pydantic validation errors into the same envelope shape.
        details = [
            {"field": ".".join(str(p) for p in err.get("loc", []) if p != "body"), "issue": err.get("msg", "invalid")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("VALIDATION_ERROR", "Request validation failed", details),
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        # If the raiser already passed a structured dict (e.g. {"code":..., "message":...}) honor it;
        # otherwise fall back to a sensible default derived from the status code.
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            code = detail["code"]
            message = detail["message"]
            details = detail.get("details", [])
        else:
            code = _STATUS_CODE_DEFAULTS.get(exc.status_code, "ERROR")
            message = detail if isinstance(detail, str) else code.replace("_", " ").title()
            details = []
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, message, details),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
        )
