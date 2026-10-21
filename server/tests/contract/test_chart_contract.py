from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from tests.conftest import seed_checks

SPEC = yaml.safe_load(
    (Path(__file__).resolve().parents[3] / "specs/002-uptime-line-charts/contracts/openapi.yaml").read_text()
)
HOST = "angels-bureau.com"


def chart_validator() -> Draft202012Validator:
    node = SPEC["paths"]["/api/domains/{hostname}/chart"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    return Draft202012Validator({**node, "components": SPEC["components"]})


async def test_chart_contract_each_range(api_client, pool):
    await seed_checks(pool, HOST, [(f"{i * 5} seconds", i % 7 != 0) for i in range(1, 60)])
    for rng, bucket in (("1h", 30), ("24h", 300), ("7d", 1800)):
        r = await api_client.get(f"/api/domains/{HOST}/chart?range={rng}")
        assert r.status_code == 200
        body = r.json()
        chart_validator().validate(body)
        assert body["range"] == rng and body["bucket_seconds"] == bucket


async def test_chart_default_range_is_24h(api_client):
    body = (await api_client.get(f"/api/domains/{HOST}/chart")).json()
    assert body["range"] == "24h" and body["bucket_seconds"] == 300


async def test_chart_invalid_range_422(api_client):
    assert (await api_client.get(f"/api/domains/{HOST}/chart?range=30d")).status_code == 422


async def test_chart_unknown_host_404(api_client):
    r = await api_client.get("/api/domains/nope.example/chart")
    assert r.status_code == 404 and "detail" in r.json()
