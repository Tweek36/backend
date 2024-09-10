from datetime import timedelta
import json
from httpx import AsyncClient
from fastapi import status
from aioredis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.token import generate_jwt_token


async def test_register(client: AsyncClient, redis: Redis, session: AsyncSession):
    register = await client.post("/auth/register/", json={
        "username": "Test",
        "email": "test@test.com",
        "password": "123456789",
        "passwordConfirm": "123456789"
    })
    assert register.status_code == status.HTTP_201_CREATED
    register_keys = await redis.keys('register:*')
    assert len(register_keys) == 1

    token = generate_jwt_token(dict(id=register_keys[0].decode('utf-8')), timedelta(seconds=900))

    register_confirm = await client.post("/auth/register/confirm/", json={
        "token": token
    })
    assert register_confirm.status_code == status.HTTP_201_CREATED
    register_confirm_data = json.loads(await register_confirm.aread())
    assert isinstance(register_confirm_data, dict)
    assert register_confirm_data.get("refresh_token")
    assert register_confirm_data.get("access_token")
