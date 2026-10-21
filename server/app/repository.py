"""SQL access for the watchdog (hand-written, asyncpg)."""
from datetime import datetime, timedelta

import asyncpg

from app.monitor import ProbeResult


async def list_active_domains(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch("SELECT id, hostname FROM domains WHERE is_active ORDER BY hostname")


async def latest_outcomes(pool: asyncpg.Pool) -> dict[str, bool]:
    rows = await pool.fetch(
        "SELECT DISTINCT ON (d.id) d.hostname, c.is_up FROM domains d "
        "JOIN check_results c ON c.domain_id = d.id ORDER BY d.id, c.checked_at DESC"
    )
    return {r["hostname"]: r["is_up"] for r in rows}


async def insert_check_result(pool: asyncpg.Pool, domain_id: int, r: ProbeResult) -> None:
    await pool.execute(
        "INSERT INTO check_results (domain_id, is_up, status_code, response_time_ms, error) "
        "VALUES ($1, $2, $3, $4, $5)",
        domain_id, r.is_up, r.status_code, r.response_time_ms, r.error,
    )


STATUS_SQL = """
SELECT d.hostname, d.display_name,
       l.is_up, l.checked_at AS last_checked_at, l.status_code, l.response_time_ms, l.error,
       w.up_1h, w.total_1h, w.up_24h, w.total_24h
FROM domains d
LEFT JOIN LATERAL (
    SELECT is_up, checked_at, status_code, response_time_ms, error
    FROM check_results WHERE domain_id = d.id ORDER BY checked_at DESC LIMIT 1
) l ON true
LEFT JOIN LATERAL (
    SELECT count(*) FILTER (WHERE is_up AND checked_at >= now() - interval '1 hour')  AS up_1h,
           count(*) FILTER (WHERE checked_at >= now() - interval '1 hour')            AS total_1h,
           count(*) FILTER (WHERE is_up)                                              AS up_24h,
           count(*)                                                                   AS total_24h
    FROM check_results WHERE domain_id = d.id AND checked_at >= now() - interval '24 hours'
) w ON true
WHERE d.is_active
ORDER BY d.hostname
"""


def _pct(up: int, total: int) -> float | None:
    return round(100.0 * up / total, 2) if total else None


async def get_status_summary(pool: asyncpg.Pool) -> list[dict]:
    out = []
    for r in await pool.fetch(STATUS_SQL):
        out.append({
            "hostname": r["hostname"], "display_name": r["display_name"],
            "is_up": r["is_up"], "last_checked_at": r["last_checked_at"],
            "status_code": r["status_code"], "response_time_ms": r["response_time_ms"],
            "error": r["error"],
            "uptime_1h": _pct(r["up_1h"], r["total_1h"]),
            "uptime_24h": _pct(r["up_24h"], r["total_24h"]),
            "checks_24h": r["total_24h"],
        })
    return out


async def get_domain_by_hostname(pool: asyncpg.Pool, hostname: str) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT id, hostname FROM domains WHERE hostname = $1", hostname)


async def list_checks(pool: asyncpg.Pool, domain_id: int, limit: int) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT checked_at, is_up, status_code, response_time_ms, error FROM check_results "
        "WHERE domain_id = $1 ORDER BY checked_at DESC LIMIT $2",
        domain_id, limit,
    )


# range key -> (window, bucket size in seconds)
RANGES = {
    "1h": (timedelta(hours=1), 30),
    "24h": (timedelta(hours=24), 300),
    "7d": (timedelta(days=7), 1800),
}

# A silence longer than this many check intervals is "missing data", not downtime.
GAP_INTERVALS = 6


async def get_chart_points(pool: asyncpg.Pool, domain_id: int, since: datetime, bucket_seconds: int) -> list[dict]:
    rows = await pool.fetch(
        "SELECT to_timestamp(floor(extract(epoch FROM checked_at) / $3::int) * $3::int) AS t, "
        "       avg(response_time_ms) FILTER (WHERE is_up) AS avg_ms, "
        "       max(response_time_ms) FILTER (WHERE is_up) AS max_ms, "
        "       count(*) AS checks, count(*) FILTER (WHERE NOT is_up) AS down "
        "FROM check_results WHERE domain_id = $1 AND checked_at >= $2 GROUP BY 1 ORDER BY 1",
        domain_id, since, bucket_seconds,
    )
    return [
        {"t": r["t"], "avg_ms": float(r["avg_ms"]) if r["avg_ms"] is not None else None,
         "max_ms": r["max_ms"], "checks": r["checks"], "down": r["down"]}
        for r in rows
    ]


DOWNTIME_SQL = """
WITH r AS (
    SELECT checked_at, is_up, error,
           lag(checked_at) OVER w AS prev_at, lag(is_up) OVER w AS prev_up
    FROM check_results WHERE domain_id = $1 AND checked_at >= $2
    WINDOW w AS (ORDER BY checked_at)
), runs AS (
    SELECT checked_at, is_up, error,
           sum(CASE WHEN NOT is_up AND (prev_up IS DISTINCT FROM false OR checked_at - prev_at > $3) THEN 1 ELSE 0 END)
               OVER (ORDER BY checked_at) AS run
    FROM r
)
SELECT min(checked_at) AS started_at, max(checked_at) AS ended_at, count(*) AS failed_checks,
       coalesce(array_agg(DISTINCT error) FILTER (WHERE error IS NOT NULL), '{}') AS errors,
       max(checked_at) = (SELECT max(checked_at) FROM r) AND max(checked_at) > $4 AS ongoing
FROM runs WHERE NOT is_up GROUP BY run ORDER BY 1
"""

GAPS_SQL = """
SELECT prev_at AS started_at, checked_at AS ended_at FROM (
    SELECT checked_at, lag(checked_at) OVER (ORDER BY checked_at) AS prev_at
    FROM check_results WHERE domain_id = $1 AND checked_at >= $2
) s WHERE checked_at - prev_at > $3 ORDER BY 1
"""


async def get_downtime_and_gaps(
    pool: asyncpg.Pool, domain_id: int, since: datetime, now: datetime, interval_seconds: int
) -> tuple[list[dict], list[dict]]:
    gap = timedelta(seconds=interval_seconds * GAP_INTERVALS)
    downtime = await pool.fetch(DOWNTIME_SQL, domain_id, since, gap, now - gap)
    gaps = await pool.fetch(GAPS_SQL, domain_id, since, gap)
    return [dict(r) for r in downtime], [dict(r) for r in gaps]


def chart_summary(points: list[dict], downtime: list[dict], interval_seconds: int) -> dict:
    return {
        "down_periods": len(downtime),
        "total_downtime_seconds": int(sum(
            (d["ended_at"] - d["started_at"]).total_seconds() + interval_seconds for d in downtime
        )),
        "checks": sum(p["checks"] for p in points),
    }
