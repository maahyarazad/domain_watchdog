from app import repository
from tests.conftest import seed_checks


async def test_status_summary(pool):
    host = "german-emirates-club.com"
    await seed_checks(pool, host, [
        ("10 seconds", False), ("10 minutes", True), ("30 minutes", True), ("3 hours", True), ("2 days", False),
    ])
    rows = {r["hostname"]: r for r in await repository.get_status_summary(pool)}
    r = rows[host]
    assert r["is_up"] is False and r["error"] == "timeout"
    assert r["uptime_1h"] == round(100 * 2 / 3, 2)
    assert r["uptime_24h"] == 75.0 and r["checks_24h"] == 4
    assert rows["angels-bureau.com"]["uptime_24h"] is None
    assert rows["angels-bureau.com"]["is_up"] is None
