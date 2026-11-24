import pytest

from _loader import load

ex = load("t03_advanced", "ex_09_design_patterns")


def test_apply_strategy():
    assert ex.apply_strategy("half", 50) == 25
    assert ex.apply_strategy("minus10", 50) == 40
    assert ex.apply_strategy("none", 50) == 50


def test_apply_strategy_unknown():
    with pytest.raises(ValueError, match="bogus"):
        ex.apply_strategy("bogus", 1)


def test_registry_register_and_create():
    reg = ex.Registry()

    @reg.register("point")
    class Point:
        def __init__(self, x, y=0):
            self.x, self.y = x, y

    assert Point.__name__ == "Point"  # decorator returns the class unchanged
    p = reg.create("point", 1, y=2)
    assert isinstance(p, Point) and (p.x, p.y) == (1, 2)


def test_registry_unknown_name():
    reg = ex.Registry()
    with pytest.raises(KeyError):
        reg.create("nope")


def test_registries_are_independent():
    a, b = ex.Registry(), ex.Registry()
    a.register("x")(dict)
    assert a.create("x") == {}
    with pytest.raises(KeyError):
        b.create("x")


def test_event_emitter_order_and_count():
    bus = ex.EventEmitter()
    log = []
    bus.on("e", lambda v: log.append(("a", v)))
    bus.on("e", lambda v: log.append(("b", v)))
    assert bus.emit("e", 1) == 2
    assert log == [("a", 1), ("b", 1)]
    assert bus.emit("other") == 0


def test_event_emitter_unsubscribe():
    bus = ex.EventEmitter()
    log = []
    off = bus.on("e", lambda: log.append("x"))
    bus.emit("e")
    off()
    off()  # idempotent
    assert bus.emit("e") == 0
    assert log == ["x"]


def test_event_emitter_self_unsubscribe_during_emit():
    bus = ex.EventEmitter()
    log = []
    holder = {}

    def once():
        log.append("once")
        holder["off"]()

    holder["off"] = bus.on("e", once)
    bus.on("e", lambda: log.append("always"))
    assert bus.emit("e") == 2
    assert log == ["once", "always"]
    assert bus.emit("e") == 1


def test_celsius_adapter():
    class Legacy:
        def read_fahrenheit(self):
            return 212.0

    assert ex.CelsiusAdapter(Legacy()).read_celsius() == 100.0


def test_notification_service_injection():
    sent = []

    def sender(to, msg):
        sent.append((to, msg))
        return to != "bad@x"

    svc = ex.NotificationService(sender)
    failed = svc.notify_all(["a@x", "bad@x", "c@x"], "hi")
    assert failed == ["bad@x"]
    assert sent == [("a@x", "hi"), ("bad@x", "hi"), ("c@x", "hi")]
