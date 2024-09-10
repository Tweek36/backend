import asyncio
from typing import Optional
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from sqlalchemy import delete, func, select
from app.config import settings
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from uuid import UUID
from enum import IntEnum
from app.database import db_manager
from app.models.tests import ProhibitedTokens


httpbearer = HTTPBearer()
optional_httpbearer = HTTPBearer(auto_error=False)


class Token(BaseModel):
    sub: UUID
    exp: datetime
    iat: datetime
    token: str


class RefreshToken(Token): ...


class AccessLevels(IntEnum):
    BANNED = -1
    UNAUTHORIZED = 0
    AUTHORIZED = 1


class AccessToken(Token):
    access_lvl: AccessLevels


def generate_jwt_token(data: dict, expires_delta: timedelta):
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "iat": datetime.utcnow(), **data}
    encoded_jwt = encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def generate_infinite_jwt_token(data: dict):
    to_encode = {"iat": datetime.utcnow(), **data}
    encoded_jwt = encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str):
    try:
        data = decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )
    return data


async def get_refresh_token_data(
    refresh_token: HTTPAuthorizationCredentials = Depends(httpbearer),
):
    try:
        data = decode_jwt_token(refresh_token.credentials)
        if data.pop("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        return RefreshToken(**data, token=refresh_token.credentials)
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)


async def get_access_token_data(
    authorization: HTTPAuthorizationCredentials = Depends(httpbearer),
):
    try:
        data = decode_jwt_token(authorization.credentials)
        if data.pop("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
            )
        return AccessToken(**data, token=authorization.credentials)
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)


async def get_optional_access_token_data(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(optional_httpbearer),
) -> Optional[AccessToken]:
    if not authorization:
        return None
    try:
        data = decode_jwt_token(authorization.credentials)
        if data.pop("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
            )
        return AccessToken(**data, token=authorization.credentials)
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.detail)


def check_access_level(required_level: AccessLevels):
    async def access_level_dependency(
        token: AccessToken = Depends(get_access_token_data),
    ):
        if token.access_lvl < required_level:
            raise HTTPException(status_code=403, detail="Insufficient access level")
        return token

    return access_level_dependency


class ProhibitedTokensManager:
    def __init__(self):
        self.cleanup_task: asyncio.Task | None = None
        self.next_cleanup: datetime | None = None

    async def init(self):
        async with db_manager.session() as session:
            stmt = select(func.min(ProhibitedTokens.expiration_time))
            earliest_expiration_time = await session.scalar(stmt)
            if earliest_expiration_time:
                self.schedule_cleanup(earliest_expiration_time)

    async def _cleanup(self):
        async with db_manager.session() as session:
            stmt = delete(ProhibitedTokens).where(
                ProhibitedTokens.expiration_time < datetime.now()
            )
            await session.execute(stmt)
            await session.commit()
            stmt = select(func.min(ProhibitedTokens.expiration_time))
            earliest_expiration_time = await session.scalar(stmt)
            if earliest_expiration_time:
                self.schedule_cleanup(earliest_expiration_time)

    def schedule_cleanup(self, at: datetime):
        if self.cleanup_task:
            if (at + timedelta(minutes=1)) < self.next_cleanup:
                self.cleanup_task.cancel()
            else:
                return

        self.next_cleanup = (
            min(at + timedelta(minutes=15), self.next_cleanup)
            if self.next_cleanup
            else at + timedelta(minutes=15)
        )
        now = datetime.utcnow().replace(tzinfo=at.tzinfo)
        delay = max(timedelta(0), self.next_cleanup - now)
        self.cleanup_task = asyncio.create_task(self._delayed_cleanup(delay))

    async def _delayed_cleanup(self, delay: timedelta):
        await asyncio.sleep(delay.total_seconds())
        await self._cleanup()
        self.cleanup_task = None
        self.next_cleanup = None


prohibited_tokens_manager = ProhibitedTokensManager()
