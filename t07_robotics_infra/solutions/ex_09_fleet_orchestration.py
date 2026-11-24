"""Exercise 09: fleet orchestration building blocks (no network, no real clocks).

Tasks
1. find_stale: which devices missed their heartbeat window.
2. transition: apply an event to a device state using the TRANSITIONS table.
3. plan_rollout: deterministic canary + waves planner.
4. should_halt: failure-rate gate between rollout waves.
5. CommandQueue: per-device FIFO command queue with TTLs (injected clock).

Run: uv run pytest t07_robotics_infra -k fleet
"""

import hashlib
import math
from collections import deque
from collections.abc import Callable
from enum import StrEnum


class DeviceState(StrEnum):
    OFFLINE = "offline"
    ONLINE = "online"
    UPDATING = "updating"
    FAULT = "fault"


class IllegalTransition(ValueError):
    pass


TRANSITIONS: dict[tuple[DeviceState, str], DeviceState] = {
    (DeviceState.OFFLINE, "heartbeat"): DeviceState.ONLINE,
    (DeviceState.ONLINE, "heartbeat"): DeviceState.ONLINE,
    (DeviceState.ONLINE, "timeout"): DeviceState.OFFLINE,
    (DeviceState.ONLINE, "start_update"): DeviceState.UPDATING,
    (DeviceState.UPDATING, "update_ok"): DeviceState.ONLINE,
    (DeviceState.UPDATING, "update_failed"): DeviceState.FAULT,
    (DeviceState.FAULT, "recover"): DeviceState.ONLINE,
}


def find_stale(last_seen: dict[str, float], now: float, timeout_s: float) -> list[str]:
    """Return the sorted ids whose `now - last_seen` is strictly greater than `timeout_s`.
    A device silent for exactly `timeout_s` is NOT stale yet.
    """
    return sorted(d for d, seen in last_seen.items() if now - seen > timeout_s)


def transition(state: DeviceState, event: str) -> DeviceState:
    """Look up (state, event) in TRANSITIONS and return the next state. Raise
    IllegalTransition (with a message naming the event and state) if it is not listed.
    Must not mutate TRANSITIONS.
    """
    try:
        return TRANSITIONS[(state, event)]
    except KeyError:
        raise IllegalTransition(f"{event!r} is not allowed in state {state.value}") from None


def plan_rollout(device_ids: list[str], canary: int, wave_percents: list[int]) -> list[list[str]]:
    """Split a fleet into rollout waves.

    - Deduplicate ids, then order them by sha256(id.encode()).hexdigest() ascending, so the
      plan does not depend on the input order.
    - Wave 0 is the canary: the first `canary` devices (omitted if canary == 0; at most the
      fleet size).
    - `wave_percents` are CUMULATIVE targets, strictly increasing, ending at 100, e.g.
      [10, 50, 100]. The target device count for percent p is ceil(n * p / 100). Each wave
      holds the devices from the previous target (initially the canary count) up to the new
      target. Waves that would be empty are skipped.
    - Raise ValueError if canary < 0, wave_percents is empty, not strictly increasing, or
      does not end at 100.
    Waves never overlap and together cover every device.
    """
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
        target = math.ceil(n * pct / 100)
        if target > prev:
            waves.append(order[prev:target])
            prev = target
    return waves


def should_halt(results: dict[str, bool], max_failure_rate: float) -> bool:
    """`results` maps device id -> update succeeded. Return True if the fraction of failures
    is STRICTLY greater than `max_failure_rate`. An empty wave never halts.
    """
    if not results:
        return False
    failed = sum(1 for ok in results.values() if not ok)
    return failed / len(results) > max_failure_rate


class CommandQueue:
    """Per-device FIFO command queue. `clock()` returns the current time in seconds."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self.clock = clock
        self._queues: dict[str, deque[tuple[int, str, float]]] = {}
        self._next_id = 1

    def enqueue(self, device_id: str, name: str, ttl_s: float = 60.0) -> int:
        """Append a command that expires `ttl_s` seconds from now. Ids start at 1 and
        increase across ALL devices. Return the command id.
        """
        cmd_id = self._next_id
        self._next_id += 1
        self._queues.setdefault(device_id, deque()).append((cmd_id, name, self.clock() + ttl_s))
        return cmd_id

    def poll(self, device_id: str) -> tuple[int, str] | None:
        """Remove and return (id, name) of the oldest command that has not expired
        (expires_at > now). Expired commands met on the way are discarded. None if nothing
        is deliverable.
        """
        queue = self._queues.get(device_id, deque())
        while queue:
            cmd_id, name, expires_at = queue.popleft()
            if expires_at > self.clock():
                return cmd_id, name
        return None

    def pending(self, device_id: str) -> int:
        """Number of queued commands for the device that have NOT expired. Must not remove
        anything.
        """
        now = self.clock()
        return sum(1 for _, _, expires_at in self._queues.get(device_id, ()) if expires_at > now)
