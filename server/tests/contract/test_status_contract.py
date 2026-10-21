from tests.conftest import seed_checks
from tests.contract.helpers import inline_validator


async def test_status_matches_contract(api_client, pool):
    await seed_checks(pool, "angels-bureau.com", [("1 minute", True), ("2 minutes", False)])
    r = await api_client.get("/api/domains/status")
    assert r.status_code == 200
    body = r.json()
    inline_validator("/api/domains/status").validate(body)
    assert len(body["domains"]) == 4
    empty = next(d for d in body["domains"] if d["hostname"] == "german-industry-club.com")
    assert empty["is_up"] is None and empty["uptime_1h"] is None and empty["checks_24h"] == 0
