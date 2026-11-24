import asyncio

import pytest

from _loader import load

ex = load("t07_robotics_infra", "ex_05_async_telemetry_pipelines")


def test_buffer_rejects_unknown_policy():
    with pytest.raises(ValueError):
        ex.BoundedBuffer(3, "nope")


def test_drop_newest_keeps_backlog_and_counts():
    async def go():
        buf = ex.BoundedBuffer(3, "drop_newest")
        for i in range(5):
            await buf.put(i)
        return [await buf.get() for _ in range(3)], buf.dropped

    items, dropped = asyncio.run(go())
    assert items == [0, 1, 2] and dropped == 2


def test_drop_oldest_keeps_latest_and_counts():
    async def go():
        buf = ex.BoundedBuffer(3, "drop_oldest")
        for i in range(5):
            await buf.put(i)
        return [await buf.get() for _ in range(3)], buf.dropped, buf.queue.qsize()

    items, dropped, size = asyncio.run(go())
    assert items == [2, 3, 4] and dropped == 2 and size == 0


def test_block_policy_applies_backpressure():
    async def go():
        buf = ex.BoundedBuffer(2, "block")
        await buf.put(1)
        await buf.put(2)
        third = asyncio.create_task(buf.put(3))
        await asyncio.sleep(0.02)
        blocked = not third.done()  # producer is held back while the queue is full
        first = await buf.get()
        await asyncio.wait_for(third, 1)
        return blocked, first, buf.dropped, buf.queue.qsize()

    assert asyncio.run(go()) == (True, 1, 0, 2)


def test_close_never_drops_the_sentinel():
    async def go():
        buf = ex.BoundedBuffer(2, "drop_newest")
        await buf.put("a")
        await buf.put("b")
        closer = asyncio.create_task(buf.close())
        await asyncio.sleep(0.01)
        assert not closer.done()  # waiting for room
        got = [await buf.get(), await buf.get()]
        await asyncio.wait_for(closer, 1)
        return got, await buf.get()

    assert asyncio.run(go()) == (["a", "b"], None)


def collect_batches(queue, **kw):
    async def go():
        return [b async for b in ex.batcher(queue, **kw)]

    return go()


def test_batcher_flushes_by_size_and_on_sentinel():
    async def go():
        q: asyncio.Queue = asyncio.Queue()
        for i in range(7):
            q.put_nowait(i)
        q.put_nowait(None)
        return await collect_batches(q, max_size=3, max_wait=5)

    assert asyncio.run(go()) == [[0, 1, 2], [3, 4, 5], [6]]


def test_batcher_empty_stream_yields_nothing():
    async def go():
        q: asyncio.Queue = asyncio.Queue()
        q.put_nowait(None)
        return await collect_batches(q, max_size=3, max_wait=5)

    assert asyncio.run(go()) == []


def test_batcher_flushes_partial_batch_after_max_wait():
    async def go():
        q: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        seen: list[tuple[float, list[int]]] = []

        async def consume():
            async for batch in ex.batcher(q, max_size=100, max_wait=0.05):
                seen.append((loop.time(), batch))

        task = asyncio.create_task(consume())
        start = loop.time()
        q.put_nowait(1)
        q.put_nowait(2)
        await asyncio.sleep(0.15)  # a quiet period: batch must flush on its own
        flushed_at = [t - start for t, _ in seen]
        q.put_nowait(3)
        q.put_nowait(None)
        await asyncio.wait_for(task, 1)
        return seen, flushed_at

    seen, flushed_at = asyncio.run(go())
    assert [b for _, b in seen] == [[1, 2], [3]]
    assert len(flushed_at) == 1 and 0.04 <= flushed_at[0] < 0.14


def test_batcher_custom_sentinel():
    async def go():
        q: asyncio.Queue = asyncio.Queue()
        stop = object()
        for item in (None, 0, stop):  # None is a legitimate item here
            q.put_nowait(item)
        return await collect_batches(q, max_size=10, max_wait=1, sentinel=stop)

    assert asyncio.run(go()) == [[None, 0]]


def test_downsampler():
    d = ex.Downsampler(0.1)
    results = [d.accept(t) for t in (0.0, 0.05, 0.09, 0.1, 0.15, 0.25, 0.2)]
    assert results == [True, False, False, True, False, True, False]
    assert ex.Downsampler(0.0).accept(1.0)


def test_downsampler_rejected_samples_do_not_move_reference():
    d = ex.Downsampler(1.0)
    assert [d.accept(t) for t in (0.0, 0.9, 1.0)] == [True, False, True]


def test_clock_sync_conversion_and_jump_detection():
    state = {"mono": 100.0, "wall": 1_700_000_100.0}
    sync = ex.ClockSync(lambda: state["mono"], lambda: state["wall"])
    assert sync.offset == pytest.approx(1_700_000_000.0)
    assert sync.to_wall(105.0) == pytest.approx(1_700_000_105.0)
    state["mono"] += 10
    state["wall"] += 10
    assert sync.drift() == pytest.approx(0.0)
    state["wall"] += 3.5  # NTP stepped the wall clock forward
    assert sync.drift() == pytest.approx(3.5)
    sync.resync()
    assert sync.drift() == pytest.approx(0.0)
    assert sync.to_wall(state["mono"]) == pytest.approx(state["wall"])


def test_clock_sync_defaults_use_real_clocks():
    import time

    sync = ex.ClockSync()
    assert abs(sync.to_wall(time.monotonic()) - time.time()) < 1.0
