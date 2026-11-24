import hashlib

import pytest

from _loader import load

ex = load("t07_robotics_infra", "ex_09_fleet_orchestration")

D = ex.DeviceState


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_find_stale():
    seen = {"b": 50.0, "a": 10.0, "c": 95.0, "edge": 70.0}
    assert ex.find_stale(seen, now=100.0, timeout_s=30.0) == ["a", "b"]  # edge: exactly 30
    assert ex.find_stale({}, 100.0, 30.0) == []


def test_transition_legal_paths():
    assert ex.transition(D.OFFLINE, "heartbeat") == D.ONLINE
    state = D.ONLINE
    for event, expected in [
        ("start_update", D.UPDATING),
        ("update_failed", D.FAULT),
        ("recover", D.ONLINE),
        ("timeout", D.OFFLINE),
    ]:
        state = ex.transition(state, event)
        assert state == expected


def test_transition_illegal_raises_specific_error():
    with pytest.raises(ex.IllegalTransition, match="start_update"):
        ex.transition(D.OFFLINE, "start_update")
    with pytest.raises(ex.IllegalTransition):
        ex.transition(D.FAULT, "update_ok")
    with pytest.raises(ex.IllegalTransition):
        ex.transition(D.ONLINE, "no_such_event")
    assert (D.OFFLINE, "start_update") not in ex.TRANSITIONS  # table untouched


FLEET = [f"d{i:02d}" for i in range(20)]


def _order(ids):
    return sorted(ids, key=lambda d: hashlib.sha256(d.encode()).hexdigest())


def test_plan_rollout_sizes_and_order():
    waves = ex.plan_rollout(FLEET, canary=2, wave_percents=[10, 50, 100])
    assert [len(w) for w in waves] == [2, 8, 10]  # 10% target (2) is already the canary
    order = _order(FLEET)
    assert [d for w in waves for d in w] == order
    assert waves[0] == order[:2]


def test_plan_rollout_is_deterministic_and_covers_everyone_once():
    a = ex.plan_rollout(FLEET, 1, [25, 100])
    b = ex.plan_rollout(list(reversed(FLEET)) + FLEET[:3], 1, [25, 100])  # shuffled + dupes
    assert a == b
    flat = [d for w in a for d in w]
    assert sorted(flat) == FLEET and len(flat) == len(set(flat))
    assert [len(w) for w in a] == [1, 4, 15]


def test_plan_rollout_edge_cases():
    assert ex.plan_rollout([], 1, [100]) == []
    assert [len(w) for w in ex.plan_rollout(["a", "b", "c"], 0, [100])] == [3]
    assert [len(w) for w in ex.plan_rollout(["a", "b"], 5, [50, 100])] == [2]  # canary > fleet
    assert [len(w) for w in ex.plan_rollout(FLEET[:3], 0, [10, 20, 100])] == [1, 2]


@pytest.mark.parametrize(
    "canary,pcts",
    [(-1, [100]), (1, []), (1, [50]), (1, [50, 50, 100]), (1, [60, 40, 100])],
)
def test_plan_rollout_validation(canary, pcts):
    with pytest.raises(ValueError):
        ex.plan_rollout(FLEET, canary, pcts)


def test_should_halt():
    assert ex.should_halt({"a": True, "b": False}, 0.25) is True  # 50% > 25%
    assert ex.should_halt({"a": True, "b": True, "c": True, "d": False}, 0.25) is False  # ==
    assert ex.should_halt({"a": False}, 0.0) is True
    assert ex.should_halt({"a": True}, 0.0) is False
    assert ex.should_halt({}, 0.0) is False


def test_command_queue_fifo_and_ids():
    clock = Clock()
    q = ex.CommandQueue(clock)
    assert q.enqueue("r1", "dock") == 1
    assert q.enqueue("r2", "charge") == 2
    assert q.enqueue("r1", "pause") == 3
    assert q.pending("r1") == 2
    assert q.poll("r1") == (1, "dock")
    assert q.poll("r1") == (3, "pause")
    assert q.poll("r1") is None
    assert q.poll("unknown") is None
    assert q.poll("r2") == (2, "charge")


def test_command_queue_ttl():
    clock = Clock()
    q = ex.CommandQueue(clock)
    q.enqueue("r1", "old", ttl_s=5)
    q.enqueue("r1", "new", ttl_s=60)
    clock.now += 5  # expires_at == now counts as expired
    assert q.pending("r1") == 1
    assert q.pending("r1") == 1  # pending() does not consume
    assert q.poll("r1") == (2, "new")
    q.enqueue("r1", "late", ttl_s=1)
    clock.now += 10
    assert q.poll("r1") is None
