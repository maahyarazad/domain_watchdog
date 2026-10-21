from datetime import datetime, timedelta, timezone

from app import repository

HOST = "angels-bureau.com"
INTERVAL = 5


async def _seed(pool, start_ago_s: int, count: int, is_up: bool, step_s: int = INTERVAL):
    """Insert `count` checks starting `start_ago_s` seconds ago, `step_s` apart (oldest first)."""
    did = await pool.fetchval("SELECT id FROM domains WHERE hostname=$1", HOST)
    await pool.execute(
        "INSERT INTO check_results (domain_id, checked_at, is_up, status_code, response_time_ms, error) "
        "SELECT $1, now() - make_interval(secs => $2 - g * $3), $4, $5, $6, $7 FROM generate_series(0, $8 - 1) g",
        did, start_ago_s, step_s, is_up, 200 if is_up else None, 20 if is_up else None,
        None if is_up else "timeout", count,
    )
    return did


async def _chart(pool, did, rng):
    window, bucket = repository.RANGES[rng]
    now = datetime.now(timezone.utc)
    since = now - window
    points = await repository.get_chart_points(pool, did, since, bucket)
    downtime, gaps = await repository.get_downtime_and_gaps(pool, did, since, now, INTERVAL)
    return points, downtime, gaps, repository.chart_summary(points, downtime, INTERVAL)


async def test_single_failure_survives_7d_condensing(pool):
    await _seed(pool, 3600, 400, True)            # 400 up checks, 5 s apart
    did = await _seed(pool, 1500, 1, False)       # one failed check in the middle
    points, downtime, gaps, summary = await _chart(pool, did, "7d")
    assert len(downtime) == 1
    assert downtime[0]["failed_checks"] == 1 and downtime[0]["started_at"] == downtime[0]["ended_at"]
    assert summary["down_periods"] == 1 and summary["total_downtime_seconds"] == INTERVAL
    assert sum(p["down"] for p in points) == 1


async def test_failed_run_start_end_and_errors(pool):
    await _seed(pool, 600, 20, True)              # up for 100 s ... until 500 s ago
    did = await _seed(pool, 495, 10, False)       # 10 failures 495..450 s ago
    await _seed(pool, 445, 20, True)
    _, downtime, gaps, summary = await _chart(pool, did, "1h")
    assert len(downtime) == 1 and downtime[0]["failed_checks"] == 10
    assert downtime[0]["errors"] == ["timeout"] and downtime[0]["ongoing"] is False
    assert (downtime[0]["ended_at"] - downtime[0]["started_at"]).total_seconds() == 45
    assert summary["total_downtime_seconds"] == 45 + INTERVAL
    assert gaps == []


async def test_all_failed_bucket_has_null_avg_not_zero(pool):
    did = await _seed(pool, 60, 12, False)
    points, downtime, _, _ = await _chart(pool, did, "1h")
    assert points and all(p["avg_ms"] is None and p["max_ms"] is None and p["down"] == p["checks"] for p in points)
    assert len(downtime) == 1 and downtime[0]["ongoing"] is True


async def test_silence_is_a_gap_not_downtime(pool):
    await _seed(pool, 1000, 10, True)             # up until 955 s ago
    did = await _seed(pool, 300, 10, True)        # silence of ~650 s, then up again
    _, downtime, gaps, summary = await _chart(pool, did, "1h")
    assert downtime == [] and summary["total_downtime_seconds"] == 0
    assert len(gaps) == 1 and (gaps[0]["ended_at"] - gaps[0]["started_at"]).total_seconds() > 600


async def test_failures_separated_by_gap_are_two_periods(pool):
    await _seed(pool, 1000, 5, False)
    did = await _seed(pool, 300, 5, False)
    _, downtime, gaps, _ = await _chart(pool, did, "1h")
    assert len(downtime) == 2 and len(gaps) == 1


async def test_no_rows_returns_empty(pool):
    did = await pool.fetchval("SELECT id FROM domains WHERE hostname=$1", HOST)
    points, downtime, gaps, summary = await _chart(pool, did, "24h")
    assert points == [] and downtime == [] and gaps == []
    assert summary == {"down_periods": 0, "total_downtime_seconds": 0, "checks": 0}
