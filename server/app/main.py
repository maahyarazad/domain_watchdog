import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings
from app.db import create_pool, ensure_database
from app import repository
from app.migrate import migrate
from app.monitor import Monitor, probe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("watchdog")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_database(settings.database_url)
    pool = await create_pool(settings.database_url)
    app.state.pool = pool
    try:
        await migrate(pool)
        domains = [(r["id"], r["hostname"]) for r in await repository.list_active_domains(pool)]
        async with httpx.AsyncClient() as client:
            async def probe_fn(host: str):
                return await probe(client, host, settings.check_timeout_seconds)

            async def sink(domain_id: int, result):
                await repository.insert_check_result(pool, domain_id, result)

            monitor = Monitor(domains, probe_fn, sink, settings.check_interval_seconds,
                              await repository.latest_outcomes(pool))
            app.state.monitor = monitor
            monitor.start()
            try:
                yield
            finally:
                await monitor.stop()
    finally:
        await pool.close()


app = FastAPI(title="Domain Watchdog API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(router)
