import asyncio
import logging

from app.monitor import Monitor, ProbeResult, TransitionTracker

UP = ProbeResult(True, 200, 10, None)
DOWN = ProbeResult(False, None, None, "timeout")


async def test_hanging_domain_does_not_delay_others():
    calls: dict[str, list[float]] = {"a": [], "b": []}
    loop = asyncio.get_running_loop()

    async def fake_probe(host):
        calls[host].append(loop.time())
        if host == "a":
            await asyncio.sleep(3600)
        return UP

    async def sink(domain_id, result):
        pass

    m = Monitor([(1, "a"), (2, "b")], fake_probe, sink, interval=0.05, last_states={})
    m.start()
    await asyncio.sleep(0.4)
    await m.stop()
    assert len(calls["a"]) == 1
    assert len(calls["b"]) >= 5


async def test_overrun_skips_slots_without_burst():
    starts: list[float] = []
    loop = asyncio.get_running_loop()
    n = 0

    async def slow_once(host):
        nonlocal n
        starts.append(loop.time())
        n += 1
        if n == 1:
            await asyncio.sleep(0.23)  # overruns ~4 intervals
        return UP

    async def sink(domain_id, result):
        pass

    m = Monitor([(1, "a")], slow_once, sink, interval=0.05, last_states={})
    m.start()
    await asyncio.sleep(0.5)
    await m.stop()
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    assert all(g > 0.03 for g in gaps)  # no back-to-back burst


def test_transition_logging(caplog):
    t = TransitionTracker({})
    with caplog.at_level(logging.WARNING, logger="watchdog.monitor"):
        t.observe("h", True)
        t.observe("h", True)
        assert not caplog.records
        t.observe("h", False)
        t.observe("h", False)
        t.observe("h", True)
    msgs = [r.getMessage() for r in caplog.records]
    assert len(msgs) == 2 and "DOWN" in msgs[0] and "RECOVERED" in msgs[1]
