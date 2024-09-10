from asyncio import Task
from typing import Optional

import pytest
from httpx import AsyncClient, ASGITransport
from yarl import URL

from alembic.command import upgrade
from tests.db_utils import alembic_config_from_url, tmp_database

from app.config import settings
from app.database import db_manager, redis_manager
from app.models.tests import Base

from fakeredis import FakeAsyncRedis

@pytest.fixture(scope="session", autouse=True)
def anyio_backend():
    return "asyncio", {"use_uvloop": True}


@pytest.fixture(scope="session")
def pg_url():
    return URL(settings.DATABASE_URL)


@pytest.fixture(scope="session")
async def migrated_postgres_template(pg_url):
    async with tmp_database(pg_url, "pytest") as tmp_url:
        alembic_config = alembic_config_from_url(tmp_url)
        settings.DATABASE_URL = tmp_url

        upgrade(alembic_config, "head")
        await MIGRATION_TASK

        yield tmp_url


@pytest.fixture(scope="session")
async def sessionmanager_for_tests(migrated_postgres_template):
    db_manager.init(db_url=migrated_postgres_template)
    yield db_manager
    await db_manager.close()


@pytest.fixture()
async def session(sessionmanager_for_tests):
    async with db_manager.session() as session:
        yield session
    async with db_manager.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        await conn.commit()


# Explained in supporting article
MIGRATION_TASK: Optional[Task] = None

@pytest.fixture()
async def redis():
    fake_redis = FakeAsyncRedis(host="redis://test")
    yield fake_redis
    await fake_redis.aclose()

@pytest.fixture()
def app(redis):
    from main import app
    redis_manager._redis = redis
    yield app


@pytest.fixture()
async def client(session, app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
