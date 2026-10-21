import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

log = logging.getLogger("watchdog.monitor")

USER_AGENT = "domain-watchdog/1.0"


@dataclass(frozen=True)
class ProbeResult:
    is_up: bool
    status_code: int | None
    response_time_ms: int | None
    error: str | None


def _classify_connect_error(exc: httpx.ConnectError) -> str:
    text = str(exc).lower()
    dns_markers = ("name or service not known", "nodename nor servname", "temporary failure in name",
                   "getaddrinfo", "no address associated", "name resolution")
    return "dns_error" if any(m in text for m in dns_markers) else "connection_error"


async def probe(client: httpx.AsyncClient, hostname: str, timeout: float) -> ProbeResult:
    start = time.perf_counter()
    try:
        resp = await client.get(
            f"http://{hostname}/",
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
        )
    except httpx.TimeoutException:
        return ProbeResult(False, None, None, "timeout")
    except httpx.ConnectError as exc:
        return ProbeResult(False, None, None, _classify_connect_error(exc))
    except (httpx.NetworkError, httpx.RemoteProtocolError):
        return ProbeResult(False, None, None, "connection_error")
    except Exception as exc:  # noqa: BLE001 - any failure is a "down" result
        return ProbeResult(False, None, None, f"error: {type(exc).__name__}")
    elapsed = int((time.perf_counter() - start) * 1000)
    if resp.status_code < 400:
        return ProbeResult(True, resp.status_code, elapsed, None)
    return ProbeResult(False, resp.status_code, elapsed, f"http_{resp.status_code}")


class TransitionTracker:
    """Remembers last outcome per host and warns on up<->down changes (FR-014)."""

    def __init__(self, initial: dict[str, bool]):
        self._state = dict(initial)

    def observe(self, hostname: str, is_up: bool) -> None:
        prev = self._state.get(hostname)
        self._state[hostname] = is_up
        if prev is True and not is_up:
            log.warning("domain DOWN: %s", hostname)
        elif prev is False and is_up:
            log.warning("domain RECOVERED: %s", hostname)


ProbeFn = Callable[[str], Awaitable[ProbeResult]]
SinkFn = Callable[[int, ProbeResult], Awaitable[None]]


class Monitor:
    def __init__(
        self,
        domains: list[tuple[int, str]],
        probe_fn: ProbeFn,
        sink: SinkFn,
        interval: float,
        last_states: dict[str, bool],
    ):
        self._domains = domains
        self._probe = probe_fn
        self._sink = sink
        self._interval = interval
        self._tracker = TransitionTracker(last_states)
        self._tasks: list[asyncio.Task] = []

    @property
    def running(self) -> bool:
        return bool(self._tasks) and all(not t.done() for t in self._tasks)

    def start(self) -> None:
        self._tasks = [asyncio.create_task(self._run(d, h), name=f"monitor:{h}") for d, h in self._domains]
        log.info("started %d monitor tasks", len(self._tasks))

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def _run(self, domain_id: int, hostname: str) -> None:
        loop = asyncio.get_running_loop()
        next_run = loop.time()
        while True:
            try:
                result = await self._probe(hostname)
                self._tracker.observe(hostname, result.is_up)
                await self._sink(domain_id, result)
            except asyncio.CancelledError:
                raise
            except Exception:  # keep the loop alive (e.g. DB outage)
                log.exception("check for %s failed to complete/store", hostname)
            next_run += self._interval
            now = loop.time()
            if next_run <= now:  # overran: skip to next future slot, no burst
                missed = int((now - next_run) / self._interval) + 1
                next_run += missed * self._interval
            await asyncio.sleep(max(0.0, next_run - loop.time()))
