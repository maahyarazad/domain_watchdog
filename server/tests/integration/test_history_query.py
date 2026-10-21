from app import repository
from tests.conftest import seed_checks


async def test_history_newest_first_and_limit(pool):
    host = "angels-bureau.com"
    await seed_checks(pool, host, [("3 minutes", True), ("1 minute", False), ("2 minutes", True)])
    d = await repository.get_domain_by_hostname(pool, host)
    rows = await repository.list_checks(pool, d["id"], 2)
    assert len(rows) == 2
    assert rows[0]["checked_at"] > rows[1]["checked_at"] and rows[0]["is_up"] is False
