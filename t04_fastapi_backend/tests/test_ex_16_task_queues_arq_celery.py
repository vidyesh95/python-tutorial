import asyncio

from _loader import load

ex = load("t04_fastapi_backend", "ex_16_task_queues_arq_celery")


def test_backoff_delay_grows_and_caps():
    assert [ex.backoff_delay(n) for n in (1, 2, 3, 4)] == [0.5, 1.0, 2.0, 4.0]
    assert ex.backoff_delay(10, base=1.0, cap=5.0) == 5.0


def test_enqueue_is_idempotent():
    async def scenario():
        q = ex.JobQueue()
        first = await q.enqueue("j1", {"n": 1})
        again = await q.enqueue("j1", {"n": 999})
        await q.close()
        items = [await q.get(), await q.get()]
        return first, again, items

    first, again, items = asyncio.run(scenario())
    assert first is True and again is False
    assert items == [("j1", {"n": 1}), None]


def test_run_job_retries_with_backoff_then_succeeds():
    calls, sleeps = [], []

    async def flaky(payload):
        calls.append(payload)
        if len(calls) < 3:
            raise ConnectionError("down")
        return "ok"

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    status = asyncio.run(ex.run_job(flaky, {"x": 1}, max_tries=5, sleep=fake_sleep))
    assert status == ("done", 3)
    assert sleeps == [0.5, 1.0]  # slept after attempts 1 and 2 only


def test_run_job_gives_up_without_raising():
    sleeps = []

    async def always_fails(payload):
        raise RuntimeError("permanent")

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    status = asyncio.run(ex.run_job(always_fails, {}, max_tries=3, sleep=fake_sleep))
    assert status == ("failed", 3)
    assert len(sleeps) == 2  # no sleep after the final failure


def test_worker_processes_until_sentinel():
    seen: list[int] = []

    async def handler(payload):
        if payload["n"] == 2:
            raise ValueError("bad job")
        seen.append(payload["n"])

    async def no_sleep(seconds):
        return None

    async def scenario():
        q, results = ex.JobQueue(), {}
        for n in (1, 2, 3):
            await q.enqueue(f"job-{n}", {"n": n})
        await q.enqueue("job-1", {"n": 1})  # duplicate: ignored
        await q.close()
        await ex.worker(q, handler, results, max_tries=2, sleep=no_sleep)
        return results

    results = asyncio.run(scenario())
    assert results == {"job-1": "done", "job-2": "failed", "job-3": "done"}
    assert seen == [1, 3]
