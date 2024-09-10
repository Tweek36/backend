from aioredis import Redis
from fastapi import APIRouter, status, Depends
from app.database import get_async_session, get_redis
from app.schemas.auth import (
    AccessRefreshTokensResponseSchema,
    AccessTokenResponseSchema,
    CreateUserSchema,
    EmailPayloadSchema,
    LoginUserSchema,
    LogoutPayloadSchema,
    ResetPasswordSchema,
    TokenSchema,
)
from app.services.auth import AuthService
from app.utils.token import RefreshToken, get_refresh_token_data
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/auth", tags=["Authorization"])


@router.post("/register/", status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: CreateUserSchema, service: AuthService = Depends(AuthService.get_service)
):
    return await service.register_user(payload)


@router.post(
    "/register/confirm/",
    status_code=status.HTTP_201_CREATED,
    response_model=AccessRefreshTokensResponseSchema,
)
async def confirm_registration(
    payload: TokenSchema,
    service: AuthService = Depends(AuthService.get_service),
):
    return await service.confirm_registration(payload)


@router.post("/login/", response_model=AccessRefreshTokensResponseSchema)
async def login(
    payload: LoginUserSchema,
    service: AuthService = Depends(AuthService.get_service),
):
    return await service.login(payload)


@router.post("/refresh/", response_model=AccessTokenResponseSchema)
async def refresh_token(
    refresh_token: RefreshToken = Depends(get_refresh_token_data),
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis)
):
    return await AuthService(session, redis, None).refresh_token(refresh_token)


@router.post("/reset_password/start/")
async def start_reset_password(
    payload: EmailPayloadSchema,
    service: AuthService = Depends(AuthService.get_service),
):
    return await service.start_reset_password(payload.email)


@router.post("/reset_password/check/")
async def check_reset_password(
    payload: TokenSchema,
    service: AuthService = Depends(AuthService.get_service),
):
    return await service.check_reset_password(payload.token)


@router.post("/reset_password/", response_model=AccessRefreshTokensResponseSchema)
async def reset_password(
    payload: ResetPasswordSchema,
    service: AuthService = Depends(AuthService.get_service),
):
    return await service.reset_password(payload)


@router.post("/logout/")
async def logout(
    payload: LogoutPayloadSchema,
    service: AuthService = Depends(AuthService.get_service),
):
    return await service.logout(payload)
