import httpx
import pytest
import respx

from app.monitor import probe

HOST = "example.test"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(follow_redirects=False) as c:
        yield c


@respx.mock
@pytest.mark.parametrize("status", [200, 301])
async def test_below_400_is_up(client, status):
    respx.get(f"http://{HOST}/").mock(return_value=httpx.Response(status))
    r = await probe(client, HOST, 4)
    assert r.is_up and r.status_code == status and r.error is None
    assert r.response_time_ms is not None and r.response_time_ms >= 0


@respx.mock
@pytest.mark.parametrize("status", [404, 503])
async def test_error_status_is_down(client, status):
    respx.get(f"http://{HOST}/").mock(return_value=httpx.Response(status))
    r = await probe(client, HOST, 4)
    assert not r.is_up and r.status_code == status and r.error == f"http_{status}"


@respx.mock
@pytest.mark.parametrize(
    "exc,expected",
    [
        (httpx.ReadTimeout("t"), "timeout"),
        (httpx.ConnectTimeout("t"), "timeout"),
        (httpx.ConnectError("[Errno 8] nodename nor servname provided, or not known"), "dns_error"),
        (httpx.ConnectError("Connection refused"), "connection_error"),
        (RuntimeError("boom"), "error: RuntimeError"),
    ],
)
async def test_failures(client, exc, expected):
    respx.get(f"http://{HOST}/").mock(side_effect=exc)
    r = await probe(client, HOST, 4)
    assert not r.is_up and r.status_code is None and r.response_time_ms is None
    assert r.error == expected
