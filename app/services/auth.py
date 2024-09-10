from datetime import timedelta
import json
from pydantic import validate_email
from sqlalchemy import select
from app.schemas.auth import (
    AccessRefreshTokensResponseSchema,
    AccessTokenResponseSchema,
    CreateUserSchema,
    LoginUserSchema,
    LogoutPayloadSchema,
    ResetPasswordSchema,
    TokenSchema,
)
from app.services import BaseService
from app.models.tests import ProhibitedTokens, User
from fastapi import status, HTTPException
from app.utils.email import send_email
from app.utils.password import get_password_hash, verify_password
from app.config import settings
from app.utils.redis import generate_unique_redis_key
from app.utils.token import (
    AccessToken,
    prohibited_tokens_manager,
    RefreshToken,
    decode_jwt_token,
    generate_jwt_token,
)


class AuthService(BaseService):
    @staticmethod
    def _generate_refresh_token(sub: str):
        return generate_jwt_token(
            dict(sub=sub, type="refresh"),
            timedelta(minutes=settings.REFRESH_TOKEN_EXPIRES_IN),
        )

    @staticmethod
    def _generate_access_token(sub: str, access_lvl: int):
        return generate_jwt_token(
            dict(sub=sub, access_lvl=access_lvl, type="access"),
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_IN),
        )

    async def register_user(self, payload: CreateUserSchema):
        stmt = select(User).filter(User.email == payload.email.lower())
        user = await self.session.scalar(stmt)
        if user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account already exist"
            )

        if payload.password != payload.passwordConfirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
            )

        hashed_password = get_password_hash(payload.password)
        del payload.passwordConfirm
        del payload.password
        payload.email = payload.email.lower()
        data = dict(
            **payload.model_dump(), hashed_password=hashed_password, access_lvl=0
        )
        redis_id = await generate_unique_redis_key(self.redis, "register")
        await self.redis.set(redis_id, json.dumps(data), ex=900)
        token = generate_jwt_token(dict(id=redis_id), timedelta(seconds=900))
        await send_email(
            to_email=payload.email,
            subject=payload.username,
            body=settings.REGISTRATION_TOKEN_PATH + token,
        )
        return True

    async def confirm_registration(self, payload: TokenSchema):
        data = decode_jwt_token(payload.token)
        redis_data = await self.redis.get(data.get("id"))
        if not redis_data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The token has been used or expired")
        user_data = json.loads(redis_data)
        new_user = User(**user_data)
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        user_id = str(new_user.id)
        refresh_token = self._generate_refresh_token(sub=user_id)
        access_token = self._generate_access_token(
            sub=user_id, access_lvl=new_user.access_lvl
        )
        await self.redis.delete(data.get("id"))
        return AccessRefreshTokensResponseSchema(
            refresh_token=refresh_token, access_token=access_token
        )

    async def login(self, payload: LoginUserSchema):
        try:
            email = validate_email(payload.username)[1]
            stmt = select(User).filter(User.email == email.lower())
        except Exception:
            stmt = select(User).filter(User.username == payload.username)

        user = await self.session.scalar(stmt)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid password")

        user_id = str(user.id)
        refresh_token = self._generate_refresh_token(sub=user_id)
        access_token = self._generate_access_token(
            sub=user_id, access_lvl=user.access_lvl
        )
        return AccessRefreshTokensResponseSchema(
            refresh_token=refresh_token, access_token=access_token
        )

    async def refresh_token(self, refresh_token: RefreshToken):
        user = await self.session.get(User, refresh_token.sub)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
        user_id = str(user.id)
        access_token = self._generate_access_token(
            sub=user_id, access_lvl=user.access_lvl
        )
        return AccessTokenResponseSchema(access_token=access_token)

    async def get_anonimus_token(self):
        access_token = self._generate_access_token(sub=None, access_lvl=0)
        return AccessTokenResponseSchema(access_token=access_token)

    async def start_reset_password(self, email: str):
        stmt = select(User).filter(User.email == email.lower())
        user = await self.session.scalar(stmt)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account does not exist"
            )
        redis_id = await generate_unique_redis_key(self.redis, "register")
        await self.redis.set(redis_id, user.email, ex=900)
        token = generate_jwt_token(dict(id=redis_id), timedelta(seconds=900))
        await send_email(
            to_email=email,
            subject=user.username,
            body=settings.PASS_RESTORE_TOKEN_PATH + token,
        )
        return True

    async def check_reset_password(self, token: str):
        data = decode_jwt_token(token)
        redis_data = await self.redis.get(data.get("id"))
        if not redis_data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The token has been used or expired")
        email = (redis_data).decode("utf-8")
        try:
            validate_email(email)[1]
        except Exception:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
            )
        return True

    async def reset_password(self, payload: ResetPasswordSchema):
        data = decode_jwt_token(payload.token)
        redis_data = await self.redis.get(data.get("id"))
        if not redis_data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The token has been used or expired")
        email = (redis_data).decode("utf-8")
        try:
            validate_email(email)[1]
        except Exception:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
            )

        if payload.password != payload.passwordConfirm:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
            )

        stmt = select(User).filter(User.email == email.lower())
        user = await self.session.scalar(stmt)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account does not exist"
            )
        hashed_password = get_password_hash(payload.password)
        user.hashed_password = hashed_password
        await self.session.commit()
        await self.session.refresh(user)
        user_id = str(user.id)
        refresh_token = self._generate_refresh_token(sub=user_id)
        access_token = self._generate_access_token(
            sub=user_id, access_lvl=user.access_lvl
        )
        return AccessRefreshTokensResponseSchema(
            refresh_token=refresh_token, access_token=access_token
        )

    async def logout(self, payload: LogoutPayloadSchema):
        try:
            access_data = AccessToken(**decode_jwt_token(payload.access_token))
        except Exception:
            access_data = None

        try:
            refresh_data = RefreshToken(**decode_jwt_token(payload.access_token))
        except Exception:
            refresh_data = None

        if access_data and refresh_data and (access_data.sub != refresh_data.sub):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token combination",
            )

        if access_data:
            if not access_data.sub:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            user = await self.session.get(User, access_data.sub)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            self.session.add(
                ProhibitedTokens(
                    token=payload.access_token,
                    expiration_time=access_data.exp,
                    created_by=access_data.sub,
                    updated_by=access_data.sub,
                )
            )
            prohibited_tokens_manager.schedule_cleanup(access_data.exp)

        if refresh_data:
            self.session.add(
                ProhibitedTokens(
                    token=payload.refresh_token,
                    expiration_time=refresh_data.exp,
                    created_by=refresh_data.sub,
                    updated_by=refresh_data.sub,
                )
            )
            prohibited_tokens_manager.schedule_cleanup(refresh_data.exp)

        await self.session.commit()
        return True
