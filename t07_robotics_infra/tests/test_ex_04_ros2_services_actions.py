import asyncio

import pytest

from _loader import load

ex = load("t07_robotics_infra", "ex_04_ros2_services_actions")
S = ex.GoalStatus


def test_call_service_returns_response():
    async def double(x: int) -> int:
        return x * 2

    assert asyncio.run(ex.call_service(double, 4, timeout=0.5)) == 8


def test_call_service_times_out():
    async def hang(_: int) -> int:
        await asyncio.sleep(1)
        return 0

    with pytest.raises(ex.ServiceTimeout):
        asyncio.run(ex.call_service(hang, 1, timeout=0.02, retries=1))


def test_call_service_retries_until_success():
    calls = {"n": 0}

    async def flaky(x: int) -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            await asyncio.sleep(1)  # first attempt hangs
        return x

    assert asyncio.run(ex.call_service(flaky, 5, timeout=0.03, retries=2)) == 5
    assert calls["n"] == 2


def test_call_service_does_not_swallow_handler_errors():
    async def bad(_: int) -> int:
        raise ValueError("broken handler")

    calls = {"n": 0}

    async def counting(x: int) -> int:
        calls["n"] += 1
        return await bad(x)

    with pytest.raises(ValueError, match="broken handler"):
        asyncio.run(ex.call_service(counting, 1, timeout=0.5, retries=3))
    assert calls["n"] == 1  # a handler error is not a timeout: no retry


async def _steps(handle):
    total = 0
    for i in range(handle.goal):
        if handle.cancel_requested:
            break
        total += 1
        handle.publish_feedback(i)
        await asyncio.sleep(0.005)
    return total


def test_goal_succeeds_with_feedback_and_result():
    async def main():
        server = ex.ActionServer(_steps)
        handle = server.send_goal(4)
        assert handle.status == S.ACCEPTED  # send_goal returns before the goal runs
        assert await handle.wait() == S.SUCCEEDED
        return handle

    handle = asyncio.run(main())
    assert handle.feedback == [0, 1, 2, 3]
    assert handle.result == 4


def test_cancel_mid_flight_gives_canceled_and_partial_result():
    async def main():
        server = ex.ActionServer(_steps)
        handle = server.send_goal(1000)
        await asyncio.sleep(0.03)
        assert handle.status == S.EXECUTING
        assert handle.request_cancel() is True
        assert handle.status == S.CANCELING
        assert await handle.wait() == S.CANCELED
        assert handle.request_cancel() is False  # too late: already finished
        assert handle.status == S.CANCELED
        return handle

    handle = asyncio.run(main())
    assert 0 < handle.result < 1000


def test_cancel_before_start_never_runs_execute():
    ran = []

    async def execute(handle):
        ran.append(1)
        return "x"

    async def main():
        handle = ex.ActionServer(execute).send_goal("g")
        assert handle.request_cancel() is True  # still ACCEPTED
        assert await handle.wait() == S.CANCELED
        return handle

    handle = asyncio.run(main())
    assert ran == [] and handle.result is None


def test_cancel_after_success_is_refused():
    async def main():
        handle = ex.ActionServer(_steps).send_goal(2)
        assert await handle.wait() == S.SUCCEEDED
        assert handle.request_cancel() is False
        assert handle.status == S.SUCCEEDED

    asyncio.run(main())


def test_failing_execute_aborts():
    async def execute(handle):
        raise RuntimeError("motor fault")

    async def main():
        handle = ex.ActionServer(execute).send_goal(1)
        assert await handle.wait() == S.ABORTED
        return handle

    assert asyncio.run(main()).result is None


def test_rejected_goal():
    async def main():
        server = ex.ActionServer(_steps, accept=lambda g: g > 0)
        with pytest.raises(ex.GoalRejected):
            server.send_goal(-1)
        return await server.send_goal(1).wait()

    assert asyncio.run(main()) == S.SUCCEEDED


def test_parameter_store_validation():
    params = ex.ParameterStore()
    params.declare("max_speed", 0.8, validator=lambda v: isinstance(v, float) and 0 < v <= 2.0)
    params.declare("name", "robot1")
    assert params.get("max_speed") == 0.8
    assert params.set("max_speed", 1.5) == (True, "")
    ok, reason = params.set("max_speed", 100.0)
    assert ok is False and "max_speed" in reason
    assert params.get("max_speed") == 1.5  # the rejected change did not apply
    assert params.set("name", "robot2") == (True, "")
    ok, reason = params.set("missing", 1)
    assert ok is False and reason
    with pytest.raises(KeyError):
        params.get("missing")
