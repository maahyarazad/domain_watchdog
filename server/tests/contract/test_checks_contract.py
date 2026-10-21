from tests.conftest import seed_checks
from tests.contract.helpers import inline_validator, validator


async def test_checks_contract(api_client, pool):
    await seed_checks(pool, "angels-bureau.com", [(f"{i} seconds", True) for i in range(1, 121)])
    r = await api_client.get("/api/domains/angels-bureau.com/checks")
    assert r.status_code == 200
    body = r.json()
    inline_validator("/api/domains/{hostname}/checks").validate(body)
    assert len(body["checks"]) == 100


async def test_unknown_host_404(api_client):
    r = await api_client.get("/api/domains/nope.example/checks")
    assert r.status_code == 404
    validator("Error").validate(r.json())


async def test_invalid_limit_422(api_client):
    for bad in ("5000", "0"):
        assert (await api_client.get(f"/api/domains/angels-bureau.com/checks?limit={bad}")).status_code == 422
