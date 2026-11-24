"""Exercise 04: services, actions (goal/feedback/result/cancel) and parameters.

Everything runs on asyncio, no ROS install needed. The skeletons are given; fill the stubs.

Tasks
1. call_service: await a handler with a timeout and optional retries.
2. GoalHandle.publish_feedback / request_cancel: goal bookkeeping and cancel semantics.
3. ActionServer.send_goal / _run: accept or reject, run the goal, and set the final status
   (SUCCEEDED, CANCELED, ABORTED).
4. ParameterStore: declare/set/get with validators that can reject a change.

Run: uv run pytest t07_robotics_infra -k ros2_services
"""

import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any


class ServiceTimeout(Exception):
    pass


class GoalRejected(Exception):
    pass


class GoalStatus(StrEnum):
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    CANCELING = "canceling"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    ABORTED = "aborted"


async def call_service(
    handler: Callable[[Any], Awaitable[Any]], request: Any, timeout: float, retries: int = 0
) -> Any:
    """Call `await handler(request)` with `timeout` seconds per attempt. On timeout retry, up
    to `retries` extra attempts. Return the first response. If every attempt times out raise
    ServiceTimeout. Exceptions raised by the handler itself must propagate unchanged
    (no retry).
    """
    raise NotImplementedError


class GoalHandle:
    def __init__(self, goal: Any) -> None:
        self.goal, self.status = goal, GoalStatus.ACCEPTED
        self.feedback: list[Any] = []
        self.result: Any = None
        self._cancel = False
        self._done = asyncio.Event()

    @property
    def cancel_requested(self) -> bool:
        return self._cancel

    async def wait(self) -> GoalStatus:
        await self._done.wait()
        return self.status

    def publish_feedback(self, fb: Any) -> None:
        """Record one feedback message (append to `self.feedback`)."""
        raise NotImplementedError

    def request_cancel(self) -> bool:
        """Only goals in ACCEPTED or EXECUTING can be canceled: set the cancel flag, move
        status to CANCELING and return True. Otherwise change nothing and return False.
        """
        raise NotImplementedError


class ActionServer:
    def __init__(
        self,
        execute: Callable[[GoalHandle], Awaitable[Any]],
        accept: Callable[[Any], bool] | None = None,
    ) -> None:
        self.execute, self.accept = execute, accept or (lambda goal: True)
        self._tasks: set[asyncio.Task[None]] = set()

    def send_goal(self, goal: Any) -> GoalHandle:
        """If accept(goal) is false raise GoalRejected. Otherwise create a GoalHandle,
        schedule `self._run(handle)` with asyncio.create_task (keep the task in
        `self._tasks` and remove it when done) and return the handle immediately.
        """
        raise NotImplementedError

    async def _run(self, handle: GoalHandle) -> None:
        """- If a cancel was requested before starting: status CANCELED, never call execute.
        - Else status EXECUTING, then handle.result = await self.execute(handle).
        - Afterwards status is CANCELED if cancel_requested else SUCCEEDED.
        - If execute raises an Exception: status ABORTED (result stays None).
        - ALWAYS set `handle._done` at the end, whatever happened.
        """
        raise NotImplementedError


class ParameterStore:
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._validators: dict[str, Callable[[Any], bool]] = {}

    def declare(
        self, name: str, default: Any, validator: Callable[[Any], bool] | None = None
    ) -> None:
        """Register `name` with `default`; no validator means everything is accepted."""
        raise NotImplementedError

    def set(self, name: str, value: Any) -> tuple[bool, str]:
        """Return (False, reason) if `name` is undeclared or the validator rejects `value`
        (the old value must stay); otherwise store it and return (True, "").
        """
        raise NotImplementedError

    def get(self, name: str) -> Any:
        """Return the current value (KeyError if undeclared)."""
        raise NotImplementedError
