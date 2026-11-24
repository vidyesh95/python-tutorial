import uuid

import pytest

serial = pytest.importorskip("serial")
can = pytest.importorskip("can")
cantools = pytest.importorskip("cantools")

from _loader import load  # noqa: E402

ex = load("t07_robotics_infra", "ex_02_serial_and_can_bus")


@pytest.fixture
def port():
    p = serial.serial_for_url("loop://", timeout=0.05)
    yield p
    p.close()


@pytest.fixture
def buses():
    channel = f"t-{uuid.uuid4().hex}"
    a = can.Bus(interface="virtual", channel=channel)
    b = can.Bus(interface="virtual", channel=channel)
    yield a, b
    a.shutdown()
    b.shutdown()


def test_nmea_checksum_and_build_line():
    assert ex.nmea_checksum("A") == "41"
    assert ex.nmea_checksum("AB") == "03"
    assert ex.build_line(["IMU", "1"]) == b"$IMU,1*" + ex.nmea_checksum("IMU,1").encode() + b"\n"


def test_parse_line_roundtrip_and_errors():
    line = ex.build_line(["GPS", "12.5", "-3.0"])
    assert ex.parse_line(line) == ["GPS", "12.5", "-3.0"]
    for bad in (b"GPS,1*00\n", b"$GPS,1\n", b"$GPS,1*00\n", b"$GPS,2*" + line[-3:]):
        with pytest.raises(ValueError):
            ex.parse_line(bad)


def test_parse_line_accepts_lowercase_hex():
    body = "X,255"
    cs = ex.nmea_checksum(body).lower()
    assert ex.parse_line(f"${body}*{cs}\r\n".encode()) == ["X", "255"]


def test_read_lines_skips_bad_and_stops_on_timeout(port):
    port.write(ex.build_line(["A", "1"]))
    port.write(b"garbage\n")
    port.write(b"$A,2*00\n")
    port.write(ex.build_line(["A", "3"]))
    port.write(b"$A,4")  # partial
    lines, bad = ex.read_lines(port, 10)
    assert lines == [["A", "1"], ["A", "3"]]
    assert bad == 2


def test_read_lines_respects_max_lines(port):
    for i in range(5):
        port.write(ex.build_line(["N", str(i)]))
    lines, bad = ex.read_lines(port, 3)
    assert [ln[1] for ln in lines] == ["0", "1", "2"] and bad == 0
    rest, _ = ex.read_lines(port, 10)
    assert [ln[1] for ln in rest] == ["3", "4"]


def test_open_with_retry_backoff_and_success():
    sleeps: list[float] = []
    calls = {"n": 0}

    def opener():
        calls["n"] += 1
        if calls["n"] < 4:
            raise serial.SerialException("busy")
        return "ok"

    assert (
        ex.open_with_retry(opener, attempts=5, base_delay=0.1, max_delay=0.3, sleep=sleeps.append)
        == "ok"
    )
    assert calls["n"] == 4
    assert sleeps == pytest.approx([0.1, 0.2, 0.3])  # capped at max_delay


def test_open_with_retry_gives_up_with_last_error():
    sleeps: list[float] = []
    calls = {"n": 0}

    def opener():
        calls["n"] += 1
        raise OSError(f"fail {calls['n']}")

    with pytest.raises(OSError, match="fail 3"):
        ex.open_with_retry(opener, attempts=3, sleep=sleeps.append)
    assert calls["n"] == 3 and len(sleeps) == 2


def test_open_with_retry_does_not_swallow_other_errors():
    sleeps: list[float] = []

    def opener():
        raise KeyError("bug")

    with pytest.raises(KeyError):
        ex.open_with_retry(opener, sleep=sleeps.append)
    assert sleeps == []


def test_encode_decode_can_roundtrip():
    db = ex.load_db()
    msg = ex.encode_can(db, "MotorCmd", {"Speed": 1500.5, "Enable": 1, "Temp": -5})
    assert msg.arbitration_id == 0x100 and not msg.is_extended_id
    assert bytes(msg.data) == bytes.fromhex("9d3a01fb")  # 15005 = 0x3A9D little-endian, enable, -5
    assert ex.decode_can(db, msg) == ("MotorCmd", {"Speed": 1500.5, "Enable": 1, "Temp": -5})


def test_decode_unknown_id_returns_none():
    db = ex.load_db()
    assert (
        ex.decode_can(db, can.Message(arbitration_id=0x7FF, data=b"\x00", is_extended_id=False))
        is None
    )


def test_encode_can_rejects_missing_or_unknown():
    db = ex.load_db()
    with pytest.raises(cantools.database.errors.EncodeError):
        ex.encode_can(db, "MotorCmd", {"Speed": 1.0})
    with pytest.raises(KeyError):
        ex.encode_can(db, "Nope", {})


def test_collect_decodes_skips_unknown_and_stops_on_silence(buses):
    ecu, motor = buses
    db = ex.load_db()
    ecu.send(ex.encode_can(db, "MotorCmd", {"Speed": 10, "Enable": 0, "Temp": 20}))
    ecu.send(can.Message(arbitration_id=0x7FF, data=b"\x01", is_extended_id=False))
    ecu.send(ex.encode_can(db, "Heartbeat", {"Counter": 7, "State": 1}))
    got = ex.collect(motor, db, count=5, timeout=0.05)
    assert [name for name, _ in got] == ["MotorCmd", "Heartbeat"]
    assert got[1][1] == {"Counter": 7, "State": 1}
    assert ex.collect(motor, db, count=1, timeout=0.05) == []


def test_collect_stops_at_count(buses):
    ecu, motor = buses
    db = ex.load_db()
    for i in range(4):
        ecu.send(ex.encode_can(db, "Heartbeat", {"Counter": i, "State": 0}))
    assert [s["Counter"] for _, s in ex.collect(motor, db, count=2, timeout=0.05)] == [0, 1]
