"""Unit tests: standard error envelope shape (architecture doc §8.4)."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from py_common.core.errors import AppError, install_error_handlers


def _build_app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    class Body(BaseModel):
        hours: float

    @app.post("/validate")
    def validate(body: Body):
        return {"ok": True}

    @app.get("/app-error")
    def app_error():
        raise AppError(400, "VALIDATION_ERROR", "Bad input", details=[{"field": "hours", "issue": "must be between 0 and 24"}])

    @app.get("/http-error")
    def http_error():
        raise HTTPException(status_code=404, detail="Not found")

    @app.get("/structured-http-error")
    def structured_http_error():
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": "Email already registered"})

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def _assert_envelope_shape(body: dict):
    assert "error" in body
    assert set(body["error"].keys()) >= {"code", "message", "details"}
    assert isinstance(body["error"]["details"], list)


def test_app_error_envelope_shape():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.get("/app-error")
    assert resp.status_code == 400
    body = resp.json()
    _assert_envelope_shape(body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"] == [{"field": "hours", "issue": "must be between 0 and 24"}]


def test_plain_http_exception_mapped_to_envelope():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.get("/http-error")
    assert resp.status_code == 404
    body = resp.json()
    _assert_envelope_shape(body)
    assert body["error"]["code"] == "NOT_FOUND"


def test_structured_http_exception_preserved():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.get("/structured-http-error")
    assert resp.status_code == 409
    body = resp.json()
    _assert_envelope_shape(body)
    assert body["error"]["code"] == "CONFLICT"
    assert body["error"]["message"] == "Email already registered"


def test_422_validation_error_mapped_to_envelope():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.post("/validate", json={"hours": "not-a-number"})
    assert resp.status_code == 422
    body = resp.json()
    _assert_envelope_shape(body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert len(body["error"]["details"]) >= 1


def test_unhandled_exception_mapped_to_500_envelope():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    _assert_envelope_shape(body)
    assert body["error"]["code"] == "INTERNAL_ERROR"
