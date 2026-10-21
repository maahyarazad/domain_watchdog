import asyncpg
from urllib.parse import urlparse, urlunparse


def _split_dsn(dsn: str) -> tuple[str, str]:
    parsed = urlparse(dsn)
    return urlunparse(parsed._replace(path="/postgres")), parsed.path.lstrip("/")


async def ensure_database(dsn: str) -> None:
    """Create the target database if it does not exist (cannot use IF NOT EXISTS)."""
    admin_dsn, name = _split_dsn(dsn)
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
        if not exists:
            await conn.execute('CREATE DATABASE "%s"' % name.replace('"', '""'))
    finally:
        await conn.close()


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)
