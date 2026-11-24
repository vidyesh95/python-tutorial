# ROS 2 Services and Actions
"""
Topics are fire-and-forget streams. When a node needs an answer, or a task takes seconds,
ROS 2 offers two more patterns built on the same transport.

SERVICES: one request -> one response (`srv` type: `request --- response`). Good for quick
queries and config changes: "reset odometry", "get map", "set mode". The call blocks the
caller's logical flow, so ALWAYS use a timeout and check `wait_for_service` first. A service
callback runs inside the executor: a slow handler stalls every other callback on that node.

ACTIONS: long-running goals with progress. An `action` type is `goal --- result --- feedback`.
Lifecycle of a goal: ACCEPTED -> EXECUTING -> SUCCEEDED | ABORTED | CANCELED, with
CANCELING in between when a cancel request arrives. The client can:
  send_goal_async -> a goal handle (or rejection); stream feedback; ask for the result;
  cancel the goal. The server decides how to honour cancellation: it must POLL
  `is_cancel_requested` inside its loop and finish with `goal_handle.canceled()` and a
  partial result. Cancel is a request, not a guarantee.
Use an action for "navigate to pose" or "pick this object"; a service would hang the caller.

PARAMETERS: typed node settings (`declare_parameter("max_speed", 1.0)`), readable and
changeable at runtime with `ros2 param set`. A `add_on_set_parameters_callback` can validate
and reject a change (return `SetParametersResult(successful=False)`).

LAUNCH FILES: Python (or XML/YAML) descriptions that start many nodes with remappings,
namespaces and parameter files: `ros2 launch my_pkg robot.launch.py`. They are how a robot
actually boots; one `Node(...)` action per process.

rclpy is not on PyPI (ROS 2 install, RoboStack, or the `ros:jazzy` image). The real-API code
below runs only if `import rclpy` works. The asyncio model after it has the same SEMANTICS
(timeouts, goal states, feedback, cancel, parameter validation) and always runs.

Common mistakes
- Calling a service with no timeout; the node hangs forever if the server dies.
- Calling a service synchronously from inside a callback on a single-threaded executor:
  deadlock. Use `call_async` or a separate callback group + MultiThreadedExecutor.
- An action server that never checks for cancel, so "cancel" does nothing.
- Using a service for something that takes minutes, or an action for a 1 ms query.
- Not validating parameters, so a typo in a YAML file sets max_speed to 100.

Production notes
- Safety: motion actions must be bounded (time and distance limits) and a watchdog must stop
  the robot if the controller stops sending commands. Cancel is NOT an emergency stop; the
  e-stop is a hardware path that does not depend on the ROS graph.
- Put a timeout on every goal; mark stuck goals ABORTED and report why.
- Make service handlers idempotent: clients retry after timeouts.
- Keep launch files declarative; pass per-robot values as parameters, not code edits.
"""

import asyncio
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

# Example 1: real rclpy service (runs only with a ROS 2 install; `example_interfaces` ships with it)
LAUNCH_FILE_EXAMPLE = """
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package="demo_nodes_py", executable="add_two_ints_server", namespace="robot1",
             parameters=[{"max_speed": 0.8}], remappings=[("add_two_ints", "math/add")]),
    ])
"""


def run_real_service_demo() -> bool:
    try:
        import rclpy
        from example_interfaces.srv import AddTwoInts
    except ImportError:
        return False
    rclpy.init()
    node = rclpy.create_node("add_demo")
    try:

        def handle(req: AddTwoInts.Request, resp: AddTwoInts.Response) -> AddTwoInts.Response:
            resp.sum = req.a + req.b
            return resp

        node.create_service(AddTwoInts, "add_two_ints", handle)
        client = node.create_client(AddTwoInts, "add_two_ints")
        if not client.wait_for_service(timeout_sec=2.0):  # never call blind
            return False
        future = client.call_async(AddTwoInts.Request(a=2, b=3))
        rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)  # bounded wait
        print("rclpy: 2 + 3 =", future.result().sum if future.done() else "timeout")
        return future.done()
    finally:
        node.destroy_node()
        rclpy.shutdown()


def make_real_fibonacci_node() -> Any | None:
    """Real rclpy action server (call after rclpy.init()); None without a ROS 2 install."""
    try:
        from example_interfaces.action import Fibonacci
        from rclpy.action import ActionServer as RosActionServer
        from rclpy.action import CancelResponse
        from rclpy.node import Node
    except ImportError:
        return None

    class FibonacciNode(Node):
        def __init__(self) -> None:
            super().__init__("fibonacci_server")
            self._server = RosActionServer(
                self,
                Fibonacci,
                "fibonacci",
                execute_callback=self.execute,
                cancel_callback=lambda goal: CancelResponse.ACCEPT,  # allow cancels
            )

        def execute(self, goal_handle: Any) -> Any:
            fb, seq = Fibonacci.Feedback(), [0, 1]
            for _ in range(goal_handle.request.order - 2):
                if goal_handle.is_cancel_requested:  # poll: cancel is cooperative
                    goal_handle.canceled()
                    return Fibonacci.Result(sequence=seq)
                seq.append(seq[-1] + seq[-2])
                fb.sequence = seq
                goal_handle.publish_feedback(fb)
            goal_handle.succeed()
            return Fibonacci.Result(sequence=seq)

    return FibonacciNode()


# Example 2: the same semantics in-process. A service is request/response with a timeout.
class ServiceTimeout(Exception):
    pass


class ServiceServer:
    def __init__(self, handler: Callable[[Any], Awaitable[Any]]) -> None:
        self.handler = handler

    async def call(self, request: Any, timeout: float = 1.0) -> Any:
        try:
            async with asyncio.timeout(timeout):
                return await self.handler(request)
        except TimeoutError as exc:
            raise ServiceTimeout(f"no response within {timeout}s") from exc


# Example 3: an action server with goal states, feedback and cancel
class GoalStatus(StrEnum):
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    CANCELING = "canceling"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    ABORTED = "aborted"


class GoalRejected(Exception):
    pass


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

    def publish_feedback(self, fb: Any) -> None:
        self.feedback.append(fb)

    def request_cancel(self) -> bool:
        if self.status not in (GoalStatus.ACCEPTED, GoalStatus.EXECUTING):
            return False  # already finished (or already canceling)
        self._cancel = True
        self.status = GoalStatus.CANCELING
        return True

    async def wait(self) -> GoalStatus:
        await self._done.wait()
        return self.status


class ActionServer:
    def __init__(
        self,
        execute: Callable[[GoalHandle], Awaitable[Any]],
        accept: Callable[[Any], bool] | None = None,
    ) -> None:
        self.execute, self.accept = execute, accept or (lambda goal: True)
        self._tasks: set[asyncio.Task[None]] = set()  # keep references so tasks are not GC'd

    def send_goal(self, goal: Any) -> GoalHandle:
        if not self.accept(goal):
            raise GoalRejected(f"goal rejected: {goal!r}")
        handle = GoalHandle(goal)
        task = asyncio.create_task(self._run(handle))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return handle

    async def _run(self, handle: GoalHandle) -> None:
        try:
            if handle.cancel_requested:  # canceled before it ever started
                handle.status = GoalStatus.CANCELED
                return
            handle.status = GoalStatus.EXECUTING
            handle.result = await self.execute(handle)
            handle.status = GoalStatus.CANCELED if handle.cancel_requested else GoalStatus.SUCCEEDED
        except Exception:
            handle.status = GoalStatus.ABORTED
        finally:
            handle._done.set()


async def fibonacci(handle: GoalHandle) -> list[int]:
    """Like the ROS Fibonacci action: feedback after every step, cooperative cancel."""
    seq = [0, 1]
    for _ in range(handle.goal - 2):
        if handle.cancel_requested:
            break  # honour the cancel and return the PARTIAL result
        seq.append(seq[-1] + seq[-2])
        handle.publish_feedback(list(seq))
        await asyncio.sleep(0.005)
    return seq


# Example 4: parameters with validation (like add_on_set_parameters_callback)
class ParameterStore:
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._validators: dict[str, Callable[[Any], bool]] = {}

    def declare(
        self, name: str, default: Any, validator: Callable[[Any], bool] | None = None
    ) -> None:
        self._values[name] = default
        self._validators[name] = validator or (lambda value: True)

    def set(self, name: str, value: Any) -> tuple[bool, str]:
        if name not in self._values:
            return False, f"parameter {name!r} not declared"
        if not self._validators[name](value):
            return False, f"value {value!r} rejected for {name!r}"
        self._values[name] = value
        return True, ""

    def get(self, name: str) -> Any:
        return self._values[name]


async def run_demo_async() -> None:
    print("real rclpy service ran:", run_real_service_demo() or "no (rclpy not installed)")

    async def slow_square(x: int) -> int:
        await asyncio.sleep(0.2 if x < 0 else 0.0)  # negative input = "hung" device
        return x * x

    srv = ServiceServer(slow_square)
    print("service 7 ->", await srv.call(7, timeout=0.1))
    try:
        await srv.call(-1, timeout=0.05)
    except ServiceTimeout as exc:
        print("service timeout:", exc)

    actions = ActionServer(fibonacci, accept=lambda n: isinstance(n, int) and 2 <= n <= 50)
    done = actions.send_goal(8)
    print("goal 8:", await done.wait(), done.result, f"({len(done.feedback)} feedback msgs)")

    cancelled = actions.send_goal(40)
    await asyncio.sleep(0.03)
    print("cancel accepted:", cancelled.request_cancel(), "status:", cancelled.status)
    print("after cancel:", await cancelled.wait(), "partial len", len(cancelled.result))
    print("cancel after finish:", cancelled.request_cancel())
    try:
        actions.send_goal(1000)
    except GoalRejected as exc:
        print(exc)

    params = ParameterStore()
    params.declare("max_speed", 0.8, validator=lambda v: isinstance(v, float) and 0 < v <= 2.0)
    print("set 1.5:", params.set("max_speed", 1.5), "| set 100.0:", params.set("max_speed", 100.0))
    print("max_speed is still", params.get("max_speed"))


def run_demo() -> None:
    asyncio.run(run_demo_async())


if __name__ == "__main__":
    run_demo()
