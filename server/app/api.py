from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app import repository
from app.config import settings
from app.schemas import ChartResponse, ChecksResponse, ErrorOut, Health, StatusResponse

router = APIRouter(prefix="/api")


@router.get("/health", response_model=Health, responses={503: {"model": Health}})
async def health(request: Request):
    try:
        await request.app.state.pool.fetchval("SELECT 1")
        database = "ok"
    except Exception:
        database = "unreachable"
    monitor_obj = getattr(request.app.state, "monitor", None)
    monitor = "running" if monitor_obj is not None and monitor_obj.running else "stopped"
    ok = database == "ok" and monitor == "running"
    body = Health(status="ok" if ok else "degraded", database=database, monitor=monitor)
    return JSONResponse(body.model_dump(), status_code=200 if ok else 503)


@router.get("/domains/status", response_model=StatusResponse)
async def domain_status(request: Request):
    domains = await repository.get_status_summary(request.app.state.pool)
    return {
        "generated_at": datetime.now(timezone.utc),
        "interval_seconds": int(settings.check_interval_seconds),
        "domains": domains,
    }


@router.get(
    "/domains/{hostname}/checks",
    response_model=ChecksResponse,
    responses={404: {"model": ErrorOut}},
)
async def domain_checks(request: Request, hostname: str, limit: int = Query(100, ge=1, le=1000)):
    pool = request.app.state.pool
    domain = await repository.get_domain_by_hostname(pool, hostname.lower())
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Unknown hostname: {hostname}")
    rows = await repository.list_checks(pool, domain["id"], limit)
    return {"hostname": domain["hostname"], "checks": [dict(r) for r in rows]}


@router.get(
    "/domains/{hostname}/chart",
    response_model=ChartResponse,
    response_model_by_alias=True,
    responses={404: {"model": ErrorOut}},
)
async def domain_chart(request: Request, hostname: str, range: Literal["1h", "24h", "7d"] = Query("24h")):
    pool = request.app.state.pool
    domain = await repository.get_domain_by_hostname(pool, hostname.lower())
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Unknown hostname: {hostname}")
    window, bucket = repository.RANGES[range]
    now = datetime.now(timezone.utc)
    since = now - window
    interval = int(settings.check_interval_seconds)
    points = await repository.get_chart_points(pool, domain["id"], since, bucket)
    downtime, gaps = await repository.get_downtime_and_gaps(pool, domain["id"], since, now, interval)
    return {
        "hostname": domain["hostname"], "range": range, "from": since, "to": now,
        "bucket_seconds": bucket, "points": points, "downtime": downtime, "gaps": gaps,
        "summary": repository.chart_summary(points, downtime, interval),
    }
