import asyncpg
import pytest
import pytest_asyncio

import os

from app.config import settings

# Reuse the credentials from .env (override with TEST_ADMIN_DSN), swapping the database name.
_base = os.environ.get("TEST_ADMIN_DSN", settings.database_url).rsplit("/", 1)[0]
ADMIN_DSN = f"{_base}/postgres"
TEST_DB = "domain_watchdog_test"
TEST_DSN = f"{_base}/{TEST_DB}"


@pytest_asyncio.fixture
async def test_dsn():
    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)')
        await admin.execute(f"CREATE DATABASE {TEST_DB}")
        yield TEST_DSN
        await admin.execute(f'DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)')
    finally:
        await admin.close()


@pytest_asyncio.fixture
async def pool(test_dsn):
    from app.db import create_pool
    from app.migrate import migrate

    p = await create_pool(test_dsn)
    await migrate(p)
    yield p
    await p.close()


@pytest_asyncio.fixture
async def api_client(pool):
    import httpx

    from app.main import app

    app.state.pool = pool
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def seed_checks(pool, hostname, rows):
    """rows: list of (age_interval_sql, is_up). status_code 200/None, error None/'timeout'."""
    did = await pool.fetchval("SELECT id FROM domains WHERE hostname=$1", hostname)
    for age, up in rows:
        await pool.execute(
            f"INSERT INTO check_results (domain_id, checked_at, is_up, status_code, response_time_ms, error) "
            f"VALUES ($1, now() - interval '{age}', $2, $3, $4, $5)",
            did, up, 200 if up else None, 20 if up else None, None if up else "timeout",
        )
