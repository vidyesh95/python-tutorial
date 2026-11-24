import asyncio

import pytest

from _loader import load

ex = load("t03_advanced", "ex_05_asyncio_deep_dive")


def test_gather_limited_order_and_limit():
    state = {"active": 0, "peak": 0}

    def make(i):
        async def job():
            state["active"] += 1
            state["peak"] = max(state["peak"], state["active"])
            await asyncio.sleep(0.005 * (5 - i))  # finish out of order
            state["active"] -= 1
            return i

        return job

    result = asyncio.run(ex.gather_limited([make(i) for i in range(5)], limit=2))
    assert result == [0, 1, 2, 3, 4]
    assert state["peak"] == 2


def test_gather_limited_propagates_errors():
    async def ok():
        return 1

    async def bad():
        raise ValueError("boom")

    with pytest.raises((ValueError, ExceptionGroup)):
        asyncio.run(ex.gather_limited([ok, bad], limit=2))


def test_first_success_skips_failures_and_cancels_rest():
    cancelled = []

    async def fails():
        await asyncio.sleep(0.001)
        raise ValueError("no")

    async def fast_ok():
        await asyncio.sleep(0.01)
        return "fast"

    async def slow():
        try:
            await asyncio.sleep(5)
            return "slow"
        except asyncio.CancelledError:
            cancelled.append(True)
            raise

    assert asyncio.run(ex.first_success([fails, slow, fast_ok])) == "fast"
    assert cancelled == [True]


def test_first_success_all_fail():
    async def fails():
        raise ValueError("no")

    with pytest.raises(RuntimeError) as info:
        asyncio.run(ex.first_success([fails, fails]))
    # NotImplementedError is a RuntimeError subclass, so require the exact type.
    assert type(info.value) is RuntimeError


def test_with_timeout():
    async def slow():
        await asyncio.sleep(1)
        return "late"

    async def quick():
        return "ok"

    async def scenario():
        timed_out = await ex.with_timeout(slow(), 0.02, "default")
        fine = await ex.with_timeout(quick(), 0.5, "default")
        return timed_out, fine

    assert asyncio.run(scenario()) == ("default", "ok")


def test_worker_pool_order_and_concurrency():
    state = {"active": 0, "peak": 0}

    async def handler(x):
        state["active"] += 1
        state["peak"] = max(state["peak"], state["active"])
        await asyncio.sleep(0.005)
        state["active"] -= 1
        return x * 2

    result = asyncio.run(ex.worker_pool(list(range(9)), handler, workers=3))
    assert result == [i * 2 for i in range(9)]
    assert state["peak"] == 3


def test_worker_pool_empty():
    async def handler(x):
        return x

    assert asyncio.run(ex.worker_pool([], handler)) == []


def test_ticks_and_collect_stream():
    async def scenario():
        gen = ex.ticks(4)
        assert hasattr(gen, "__aiter__")
        return await ex.collect_stream(gen)

    assert asyncio.run(scenario()) == [0, 1, 2, 3]
