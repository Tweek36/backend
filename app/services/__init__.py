from typing import Generic, Type, TypeVar
from uuid import UUID
from aioredis import Redis
from fastapi import Depends, HTTPException
from sqlalchemy import select, event
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session, get_redis
from app.utils.pagination import Paginator
from sqlalchemy.exc import IntegrityError
from types import FunctionType, MethodType
from asyncio import iscoroutinefunction

from app.utils.token import AccessToken, get_optional_access_token_data
from functools import wraps


class ExceptionHandlerMeta(type):
    def __new__(cls, name, bases, dct):
        for attr_name, attr_value in dct.items():
            if isinstance(attr_value, (FunctionType, MethodType)):
                if iscoroutinefunction(attr_value):
                    dct[attr_name] = cls.async_exception_handler(attr_value)
                else:
                    dct[attr_name] = cls.sync_exception_handler(attr_value)
        return super().__new__(cls, name, bases, dct)

    @staticmethod
    def sync_exception_handler(method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except IntegrityError as e:
                errors = tuple(i.split("DETAIL:")[1].lstrip() for i in e.args)
                raise HTTPException(409, errors)

        return wrapper

    @staticmethod
    def async_exception_handler(method):
        @wraps(method)
        async def wrapper(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except IntegrityError as e:
                errors = tuple(i.split("DETAIL:")[1].lstrip() for i in e.args)
                raise HTTPException(409, errors)

        return wrapper


_T = TypeVar("_T", bound=Type[DeclarativeBase])


class BaseService(metaclass=ExceptionHandlerMeta):
    _session: AsyncSession = None

    def __init__(
        self, session: AsyncSession, redis: Redis, token: AccessToken | None
    ) -> None:
        self.session = session
        self.redis = redis
        self._token = token

    @classmethod
    async def get_service(
        cls,
        session: AsyncSession = Depends(get_async_session),
        redis: Redis = Depends(get_redis),
        token: AccessToken | None = Depends(get_optional_access_token_data),
    ):
        return cls(session, redis, token)

    @property
    def token(self):
        if self._token is None:
            raise HTTPException(status_code=403, detail="Not authenticated")
        return self._token

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, value: AsyncSession):
        self._session = value

        @event.listens_for(self._session.sync_session, "before_flush")
        def before_flush(session, flush_context, instances):
            if not self._token:
                return
            for instance in session.new:
                if hasattr(instance, "created_by"):
                    instance.created_by = self.token.sub
                if hasattr(instance, "updated_by"):
                    instance.updated_by = self.token.sub

            for instance in session.dirty:
                if hasattr(instance, "updated_by"):
                    instance.updated_by = self.token.sub


class ModelRequests(Generic[_T]):
    model: Type[_T] = None
    session: AsyncSession
    redis: Redis

    def __init__(self) -> None:
        super().__init__()
        if not self.model:
            raise ValueError("model is not defined")

    async def get(self, **filters) -> _T:
        stmt = select(self.model).filter_by(**filters)
        data = await self.session.scalar(stmt)
        if not data:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found"
            )
        return data

    async def get_paginated_list(self, max_per_page: int, page: int, **filters):
        stmt = select(self.model).filter_by(**filters)
        paginator = Paginator(
            session=self.session, stmt=stmt, max_per_page=max_per_page, page=page
        )
        await paginator.execute()
        if not paginator.data:
            raise HTTPException(status_code=404, detail="Data is out of bounds")
        return paginator.response

    async def get_list(self, **filters):
        stmt = select(self.model).filter_by(**filters)
        scalars = await self.session.stream_scalars(stmt)
        data = await scalars.all()
        if not data:
            raise HTTPException(status_code=404, detail="Data is out of bounds")
        return data

    async def _post_unfushed(self, **data):
        instance = self.model(**data)
        self.session.add(instance)
        return instance

    async def post(self, **data):
        instance = await self._post_unfushed(**data)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def _update_unfushed(self, id: int | UUID, **data):
        instance = await self.session.get(self.model, id)
        if not instance:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found"
            )

        if not data:
            raise HTTPException(status_code=400, detail="No data to update")

        for k, v in data.items():
            setattr(instance, k, v)
        return instance

    async def update(self, id: int | UUID, **data):
        instance = await self._update_unfushed(id, **data)
        await self.session.commit()
        await self.session.refresh(instance)

        return instance

    async def _delete_unfushed(self, id: int | UUID):
        instance = await self.session.get(self.model, id)
        if not instance:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found"
            )
        await self.session.delete(instance)
        return True

    async def delete(self, id: int | UUID):
        return await self._delete_unfushed(id)
