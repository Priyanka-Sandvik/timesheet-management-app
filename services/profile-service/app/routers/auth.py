"""Public auth routes: register, login, login-as-admin, JWKS."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import get_auth_rate_limiter, get_auth_service
from app.models.schemas import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(tags=["auth"])

_rate_limit_dependency = get_auth_rate_limiter().as_dependency()


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_rate_limit_dependency)],
)
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    user = auth_service.register(payload)
    return RegisterResponse(email=user.email, fullName=user.full_name)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    dependencies=[Depends(_rate_limit_dependency)],
)
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    token, expires_in = auth_service.login(payload.email, payload.password)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/auth/login-as-admin",
    response_model=TokenResponse,
    dependencies=[Depends(_rate_limit_dependency)],
)
async def login_as_admin(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    token, expires_in = auth_service.login_as_admin(payload.email, payload.password)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/.well-known/jwks.json")
async def jwks(auth_service: AuthService = Depends(get_auth_service)) -> dict:
    return auth_service.get_jwks()
