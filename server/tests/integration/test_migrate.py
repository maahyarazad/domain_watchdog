import asyncpg
import pytest

from app.db import create_pool
from app.migrate import migrate


async def test_migrate_twice_and_constraints(test_dsn):
    pool = await create_pool(test_dsn)
    try:
        first = await migrate(pool)
        second = await migrate(pool)
        assert first == ["001_init"] and second == []
        async with pool.acquire() as c:
            assert await c.fetchval("SELECT count(*) FROM schema_migrations") == 1
            assert await c.fetchval("SELECT count(*) FROM domains") == 4
            did = await c.fetchval("SELECT id FROM domains LIMIT 1")
            with pytest.raises(asyncpg.CheckViolationError):
                await c.execute(
                    "INSERT INTO check_results (domain_id,is_up,status_code) VALUES ($1,false,99)", did)
            with pytest.raises(asyncpg.CheckViolationError):
                await c.execute(
                    "INSERT INTO check_results (domain_id,is_up,status_code,response_time_ms) "
                    "VALUES ($1,true,200,-1)", did)
    finally:
        await pool.close()
