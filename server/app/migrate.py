import logging
from pathlib import Path

import asyncpg

log = logging.getLogger("watchdog.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
LOCK_ID = 727_001


def pending_migrations(files: list[Path], applied: set[str]) -> list[Path]:
    """Migration files not yet applied, in filename order."""
    return [f for f in sorted(files, key=lambda p: p.name) if f.stem not in applied]


async def migrate(pool: asyncpg.Pool, directory: Path = MIGRATIONS_DIR) -> list[str]:
    applied_now: list[str] = []
    async with pool.acquire() as conn:
        await conn.execute("SELECT pg_advisory_lock($1)", LOCK_ID)
        try:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            applied = {r["version"] for r in await conn.fetch("SELECT version FROM schema_migrations")}
            for f in pending_migrations(list(directory.glob("*.sql")), applied):
                async with conn.transaction():
                    await conn.execute(f.read_text())
                    await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", f.stem)
                log.info("applied migration %s", f.stem)
                applied_now.append(f.stem)
            if not applied_now:
                log.info("database schema already up to date")
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", LOCK_ID)
    return applied_now
