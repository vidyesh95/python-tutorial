# Fleet Orchestration
"""
A fleet is many robots you cannot SSH into one by one. The control plane keeps three things
true: it knows which devices exist and are alive, it can send them work safely, and it can
change their software without bricking them all at once.

DEVICE REGISTRY + HEARTBEATS
- Each device has a stable id, a software version and a state. It sends a small HEARTBEAT
  every N seconds (battery, version, uptime). The server records `last_seen`.
- STALENESS: a device is stale when `now - last_seen > timeout`. Pick timeout as ~3x the
  heartbeat interval so one lost packet does not page anyone. Use the SERVER clock for
  `last_seen` (device clocks drift) and a MONOTONIC clock for durations if in one process.
- Inject the clock (`clock: Callable[[], float]`) so tests advance time instantly instead of
  sleeping. All the code below takes a clock.

STATE MACHINE
- Model device lifecycle as an explicit table of (state, event) -> next state. Anything not
  in the table is ILLEGAL and rejected, which makes "how did it get into UPDATING from
  OFFLINE?" a bug you catch in tests, not in the field.

    OFFLINE --heartbeat--> ONLINE --start_update--> UPDATING --update_ok--> ONLINE
                              |                        |  \\--update_failed--> FAULT
                              +--timeout--> OFFLINE    +--timeout--> FAULT --recover--> ONLINE
    any state --decommission--> DECOMMISSIONED (terminal)

OTA ROLLOUTS (over-the-air updates)
- Never update everyone at once. CANARY first (a few devices, ideally internal/low-risk),
  then WAVES of growing size (for example 10%, 50%, 100%). Between waves, watch health
  (failure rate, crash loops, heartbeat loss) and HALT automatically if it is bad.
- Make wave membership deterministic (hash of the device id) so a retry or a second planner
  picks the same canaries, and so one team's devices are not always first.
- Devices need A/B partitions or a rollback path: a failed update must boot the old image.

COMMAND QUEUES
- The control plane cannot always push (robots sit behind NAT, on flaky links), so devices
  POLL for commands or hold an outbound connection. Queue per device, FIFO, each command
  with an id and a TTL: "go to dock" is useless an hour later. The device ACKs by id;
  unacked commands are retried or expire. Commands must be idempotent.
- Wait for acks with a timeout (`asyncio.wait_for`) and treat a timeout as "unknown", not
  "failed": the command may still have run.

Common mistakes
- Treating "no heartbeat yet" as healthy, or one missed heartbeat as dead.
- Trusting device-reported time or version blindly; validate and cap what a device can claim.
- Rolling out to 100% with no health gate or no rollback; auto-retrying a bad update forever.
- Non-idempotent or non-expiring commands (a stale "start mission" replayed on reconnect).
- Mutable global state in the API: pass the registry and clock in, so tests get a fresh one.

Production notes
- SAFETY: a lost link must never leave a robot moving. Devices need their OWN watchdog
  that stops motion if commands or heartbeats from the control plane stop, plus a hardware
  e-stop. The cloud is advisory, never in the safety loop.
- Authenticate every device (mTLS or signed tokens, per-device identity), sign OTA images
  and verify on the device, and keep an audit log of who sent which command.
- Rate-limit command and heartbeat endpoints; a buggy fleet can DDoS its own control plane.
- Reconnect storms after an outage: add jitter to retry and heartbeat timers.
Real systems: AWS IoT Greengrass/Jobs, Azure IoT Hub, Mender, Balena, RoboMaker successors,
Formant/Foxglove for observability. The ideas above are what they implement.
"""

import asyncio
import hashlib
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import count

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

Clock = Callable[[], float]


class FakeClock:
    """Manual clock for tests and demos."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


# Example 1: device state machine
class DeviceState(StrEnum):
    OFFLINE = "offline"
    ONLINE = "online"
    UPDATING = "updating"
    FAULT = "fault"
    DECOMMISSIONED = "decommissioned"


class IllegalTransition(ValueError):
    pass


S = DeviceState
TRANSITIONS: dict[tuple[DeviceState, str], DeviceState] = {
    (S.OFFLINE, "heartbeat"): S.ONLINE,
    (S.ONLINE, "heartbeat"): S.ONLINE,
    (S.UPDATING, "heartbeat"): S.UPDATING,
    (S.FAULT, "heartbeat"): S.FAULT,
    (S.ONLINE, "timeout"): S.OFFLINE,
    (S.UPDATING, "timeout"): S.FAULT,
    (S.ONLINE, "start_update"): S.UPDATING,
    (S.UPDATING, "update_ok"): S.ONLINE,
    (S.UPDATING, "update_failed"): S.FAULT,
    (S.FAULT, "recover"): S.ONLINE,
    (S.OFFLINE, "decommission"): S.DECOMMISSIONED,
    (S.ONLINE, "decommission"): S.DECOMMISSIONED,
    (S.FAULT, "decommission"): S.DECOMMISSIONED,
}


def transition(state: DeviceState, event: str) -> DeviceState:
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise IllegalTransition(f"{event!r} is not allowed in state {state.value}") from None


# Example 2: registry with heartbeats and an injected clock
@dataclass
class Device:
    id: str
    version: str
    state: DeviceState = DeviceState.OFFLINE
    last_seen: float | None = None
    battery: float | None = None


class Registry:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.devices: dict[str, Device] = {}

    def register(self, device_id: str, version: str) -> Device:
        if device_id in self.devices:
            raise ValueError(f"{device_id} already registered")
        self.devices[device_id] = Device(device_id, version)
        return self.devices[device_id]

    def heartbeat(self, device_id: str, battery: float | None = None) -> Device:
        dev = self.devices[device_id]  # KeyError for unknown devices
        dev.state = transition(dev.state, "heartbeat")
        dev.last_seen = self.clock()
        dev.battery = battery
        return dev

    def stale_ids(self, timeout_s: float) -> list[str]:
        """Devices heard from before, silent for longer than the timeout. Never-seen
        devices are NOT stale (they are 'not yet online'), decommissioned ones are ignored."""
        now = self.clock()
        return sorted(
            d.id
            for d in self.devices.values()
            if d.last_seen is not None
            and now - d.last_seen > timeout_s
            and d.state is not DeviceState.DECOMMISSIONED
        )

    def sweep(self, timeout_s: float) -> list[str]:
        """Apply the 'timeout' event to stale devices where the machine allows it."""
        changed = []
        for device_id in self.stale_ids(timeout_s):
            dev = self.devices[device_id]
            if (dev.state, "timeout") in TRANSITIONS:
                dev.state = transition(dev.state, "timeout")
                changed.append(device_id)
        return changed


# Example 3: canary + waves
def plan_rollout(device_ids: list[str], canary: int, wave_percents: list[int]) -> list[list[str]]:
    """Deterministic order by hash; canary first, then waves up to cumulative percentages."""
    if canary < 0 or not wave_percents or wave_percents[-1] != 100:
        raise ValueError("need canary >= 0 and cumulative wave_percents ending at 100")
    if any(b <= a for a, b in zip(wave_percents, wave_percents[1:], strict=False)):
        raise ValueError("wave_percents must be strictly increasing")
    order = sorted(set(device_ids), key=lambda d: hashlib.sha256(d.encode()).hexdigest())
    n = len(order)
    waves: list[list[str]] = []
    prev = min(canary, n)
    if prev:
        waves.append(order[:prev])
    for pct in wave_percents:
        target = -(-n * pct // 100)  # ceil without floats
        if target > prev:
            waves.append(order[prev:target])
            prev = target
    return waves


def should_halt(results: dict[str, bool], max_failure_rate: float) -> bool:
    """True if the failed fraction of a finished wave exceeds the allowed rate."""
    if not results:
        return False
    failed = sum(1 for ok in results.values() if not ok)
    return failed / len(results) > max_failure_rate


def run_rollout(
    waves: list[list[str]], apply: Callable[[str], bool], max_failure_rate: float
) -> tuple[int, bool]:
    """Returns (waves completed, halted)."""
    for i, wave in enumerate(waves):
        results = {device_id: apply(device_id) for device_id in wave}
        if should_halt(results, max_failure_rate):
            return i, True
    return len(waves), False


# Example 4: per-device command queue with TTL
@dataclass
class Command:
    id: int
    name: str
    expires_at: float
    acked: bool = field(default=False)


class CommandQueue:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self._queues: dict[str, deque[Command]] = {}
        self._ids = count(1)

    def enqueue(self, device_id: str, name: str, ttl_s: float = 60.0) -> int:
        cmd = Command(next(self._ids), name, self.clock() + ttl_s)
        self._queues.setdefault(device_id, deque()).append(cmd)
        return cmd.id

    def poll(self, device_id: str) -> Command | None:
        """Oldest unexpired command (removed from the queue); expired ones are dropped."""
        queue = self._queues.get(device_id, deque())
        while queue:
            cmd = queue.popleft()
            if cmd.expires_at > self.clock():
                return cmd
        return None


class AckBoard:
    """Async acks: wait for a device to confirm a command, with a timeout."""

    def __init__(self) -> None:
        self._events: dict[int, asyncio.Event] = {}

    def ack(self, command_id: int) -> None:
        self._events.setdefault(command_id, asyncio.Event()).set()

    async def wait(self, command_id: int, timeout_s: float) -> bool:
        event = self._events.setdefault(command_id, asyncio.Event())
        try:
            await asyncio.wait_for(event.wait(), timeout_s)
            return True
        except TimeoutError:
            return False  # unknown outcome, NOT proof the command failed


# Example 5: a small fleet API (state is injected, so every test gets a fresh app)
class RegisterBody(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    version: str


class HeartbeatBody(BaseModel):
    battery: float | None = Field(default=None, ge=0, le=100)


class CommandBody(BaseModel):
    name: str
    ttl_s: float = Field(default=60.0, gt=0, le=3600)


def create_app(registry: Registry, queue: CommandQueue) -> FastAPI:
    app = FastAPI(title="fleet")

    def device_or_404(device_id: str) -> Device:
        if device_id not in registry.devices:
            raise HTTPException(404, f"unknown device {device_id}")
        return registry.devices[device_id]

    def view(d: Device) -> dict[str, object]:
        return {"id": d.id, "version": d.version, "state": d.state.value, "battery": d.battery}

    @app.post("/devices", status_code=201)
    def register(body: RegisterBody) -> dict[str, object]:
        try:
            return view(registry.register(body.id, body.version))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/devices")
    def list_devices(state: DeviceState | None = None) -> list[dict[str, object]]:
        return [view(d) for d in registry.devices.values() if state in (None, d.state)]

    @app.get("/devices/stale")  # declared before /devices/{device_id}
    def stale(timeout_s: float = 30.0) -> dict[str, list[str]]:
        return {"stale": registry.stale_ids(timeout_s)}

    @app.post("/devices/{device_id}/heartbeat")
    def heartbeat(device_id: str, body: HeartbeatBody) -> dict[str, object]:
        device_or_404(device_id)
        try:
            return view(registry.heartbeat(device_id, body.battery))
        except IllegalTransition as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/devices/{device_id}/commands", status_code=202)
    def send_command(device_id: str, body: CommandBody) -> dict[str, int]:
        device_or_404(device_id)
        return {"id": queue.enqueue(device_id, body.name, body.ttl_s)}

    @app.post("/devices/{device_id}/commands/poll")
    def poll(device_id: str) -> dict[str, object]:
        device_or_404(device_id)
        cmd = queue.poll(device_id)
        return {"command": None if cmd is None else {"id": cmd.id, "name": cmd.name}}

    return app


async def ack_demo() -> None:
    board = AckBoard()
    asyncio.get_running_loop().call_later(0.01, board.ack, 1)  # the device acks command 1
    print("acked in time:", await board.wait(1, timeout_s=0.5))
    print("never acked  :", await board.wait(2, timeout_s=0.05))


def run_demo() -> None:
    clock = FakeClock()
    registry, queue = Registry(clock), CommandQueue(clock)
    client = TestClient(create_app(registry, queue))

    for i in range(3):
        client.post("/devices", json={"id": f"amr-{i}", "version": "1.0.0"})
    print("duplicate ->", client.post("/devices", json={"id": "amr-0", "version": "1"}).status_code)
    print("heartbeat:", client.post("/devices/amr-0/heartbeat", json={"battery": 80}).json())
    client.post("/devices/amr-1/heartbeat", json={"battery": 55})
    print("unknown  ->", client.post("/devices/nope/heartbeat", json={}).status_code)

    clock.advance(45)  # amr-1 goes quiet, amr-0 keeps beating
    client.post("/devices/amr-0/heartbeat", json={"battery": 79})
    print("stale:", client.get("/devices/stale", params={"timeout_s": 30}).json())
    print("swept to offline:", registry.sweep(30), "->", registry.devices["amr-1"].state.value)

    client.post("/devices/amr-0/commands", json={"name": "dock", "ttl_s": 30})
    print("poll:", client.post("/devices/amr-0/commands/poll").json())
    print("poll again:", client.post("/devices/amr-0/commands/poll").json())
    client.post("/devices/amr-0/commands", json={"name": "go_home", "ttl_s": 5})
    clock.advance(10)  # the command expired before the robot polled
    print("expired:", client.post("/devices/amr-0/commands/poll").json())

    try:
        transition(DeviceState.OFFLINE, "start_update")
    except IllegalTransition as exc:
        print("illegal:", exc)

    fleet = [f"robot-{i:02d}" for i in range(20)]
    waves = plan_rollout(fleet, canary=2, wave_percents=[10, 50, 100])
    print("wave sizes:", [len(w) for w in waves], "canaries:", waves[0])
    assert waves == plan_rollout(list(reversed(fleet)), 2, [10, 50, 100])  # order-independent
    bad = {waves[2][0], waves[2][1], waves[2][2]}  # 3 of 10 fail in wave 3
    done, halted = run_rollout(waves, lambda d: d not in bad, max_failure_rate=0.2)
    print(f"rollout completed {done}/{len(waves)} waves, halted={halted}")

    asyncio.run(ack_demo())


if __name__ == "__main__":
    run_demo()
