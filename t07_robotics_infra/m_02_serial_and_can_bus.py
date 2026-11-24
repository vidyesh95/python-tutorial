# Serial and CAN Bus I/O
"""
Two links you meet on almost every robot:

SERIAL (UART / USB-CDC): a raw byte stream between your computer and a microcontroller,
GPS, IMU or motor driver. No message boundaries, no error handling beyond optional parity.
- pyserial: `serial.Serial("/dev/ttyUSB0", 115200, timeout=0.5)` for real hardware. For
  offline work `serial.serial_for_url("loop://")` gives a loopback port: what you write you
  can read back, so the lesson and its tests need no device.
- `read(n)`, `read_until(b"\\n")` and `readline()` return what arrived before `timeout`; a
  timeout returns FEWER bytes (or b""), it does not raise. Always check what you got.
- Text protocols such as NMEA use `$fields*CHECKSUM\\n`: line-delimited and easy to debug
  with a terminal, but bigger and slower than the binary framing of m_01.

CAN BUS: a multi-drop bus used in vehicles, motor controllers and BMS packs.
- A frame has an ARBITRATION ID (11-bit standard, 29-bit extended), 0-8 data bytes (64 with
  CAN FD) and a hardware CRC. The ID is not an address: it says WHAT the message is, and the
  lowest ID wins arbitration, so low IDs mean high priority.
- Nodes broadcast; every node sees every frame and uses acceptance FILTERS to keep only the
  IDs it cares about.
- A DBC file describes how signals (speed, torque, temperature) are packed into the bytes of
  each message id: start bit, length, endianness, signedness, scale and offset. `cantools`
  parses DBC text and encodes/decodes for you. Real data is `physical = raw * scale + offset`.
- python-can: `can.Bus(interface="virtual", channel="x")` is an in-memory bus. Two Bus
  instances on the same channel can talk to each other; real hardware swaps the interface
  (`socketcan`, `pcan`, `slcan`, `kvaser`) and nothing else.

Reconnect: devices unplug and USB ports re-enumerate. Wrap opening in a retry with
exponential backoff and a cap, and treat a read timeout over a longer window as a dead link.

Common mistakes
- Assuming `read()` blocks until a full message: it returns partial data after the timeout.
- No timeout at all (`timeout=None`): the thread hangs forever when the device goes quiet.
- Treating the CAN id as a device address, or ignoring that two nodes must never send the
  same id at the same time.
- Decoding with the wrong DBC version: signals silently become garbage. Check the id exists
  and the data length matches.
- Forgetting `bus.shutdown()`; the interface stays open and the next run cannot open it.

Production notes
- Run IO in a thread (`asyncio.to_thread`) or use `can.Notifier`, never in an event loop.
- Watchdog: if no heartbeat frame arrives within N ms, command a safe stop. Stale data is
  worse than no data: timestamp every frame and drop old ones.
- Add an E-STOP that does not depend on software (hardware cut) in addition to the CAN one.
- Never trust sensor data blindly: range-check decoded signals and check frame counters.
- Log raw frames (candump / MCAP, m_07) so you can replay a failure offline.
"""

import time
import uuid
from collections.abc import Callable
from typing import Any

import can
import cantools
import serial

DBC = """VERSION ""

NS_ :

BS_:

BU_: ECU MOTOR

BO_ 256 MotorCmd: 4 ECU
 SG_ Speed : 0|16@1+ (0.1,0) [0|6553.5] "rpm" MOTOR
 SG_ Enable : 16|1@1+ (1,0) [0|1] "" MOTOR
 SG_ Temp : 24|8@1- (1,0) [-128|127] "C" MOTOR

BO_ 512 Heartbeat: 2 MOTOR
 SG_ Counter : 0|8@1+ (1,0) [0|255] "" ECU
 SG_ State : 8|8@1+ (1,0) [0|255] "" ECU
"""


# Example 1: serial loopback and a checksummed text protocol
def nmea_checksum(body: str) -> str:
    value = 0
    for ch in body.encode("ascii"):
        value ^= ch
    return f"{value:02X}"


def build_line(fields: list[str]) -> bytes:
    body = ",".join(fields)
    return f"${body}*{nmea_checksum(body)}\n".encode("ascii")


def parse_line(line: bytes) -> list[str]:
    text = line.decode("ascii", errors="replace").strip()
    if not text.startswith("$") or "*" not in text:
        raise ValueError(f"malformed line: {text!r}")
    body, _, given = text[1:].rpartition("*")
    if nmea_checksum(body) != given.upper():
        raise ValueError("checksum mismatch")
    return body.split(",")


def read_lines(port: serial.SerialBase, max_lines: int) -> tuple[list[list[str]], int]:
    """Read up to max_lines valid lines; stop at the first timeout. Returns (lines, bad)."""
    good: list[list[str]] = []
    bad = 0
    while len(good) < max_lines:
        raw = port.read_until(b"\n")
        if not raw.endswith(b"\n"):  # timeout (or partial line): nothing more right now
            break
        try:
            good.append(parse_line(raw))
        except ValueError:
            bad += 1  # a noisy line must not kill the reader
    return good, bad


# Example 2: reconnect with exponential backoff (sleep is injectable so tests are instant)
def open_with_retry[T](
    opener: Callable[[], T],
    attempts: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    for attempt in range(attempts):
        try:
            return opener()
        except (OSError, serial.SerialException) as exc:
            if attempt == attempts - 1:
                raise
            delay = min(max_delay, base_delay * 2**attempt)
            print(f"  open failed ({exc}); retry in {delay:.2f}s")
            sleep(delay)
    raise AssertionError("unreachable")


# Example 3: CAN signals via a DBC
def load_db() -> Any:
    return cantools.database.load_string(DBC, database_format="dbc")


def encode_can(db: Any, name: str, signals: dict[str, float]) -> can.Message:
    msg = db.get_message_by_name(name)
    data = msg.encode(signals)  # raises if a signal is missing or out of range
    return can.Message(arbitration_id=msg.frame_id, data=data, is_extended_id=False)


def decode_can(db: Any, msg: can.Message) -> tuple[str, dict[str, Any]] | None:
    try:
        dbc_msg = db.get_message_by_frame_id(msg.arbitration_id)
    except KeyError:
        return None  # not ours: ignore frames we have no definition for
    return dbc_msg.name, dbc_msg.decode(bytes(msg.data))


# Example 4: two nodes on a virtual bus, with acceptance filters
def collect(bus: can.BusABC, db: Any, count: int, timeout: float = 0.2) -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    while len(out) < count:
        msg = bus.recv(timeout=timeout)
        if msg is None:
            break  # silence: a watchdog would trigger here
        decoded = decode_can(db, msg)
        if decoded is not None:
            out.append(decoded)
    return out


def run_demo() -> None:
    port = serial.serial_for_url("loop://", timeout=0.05)
    try:
        port.write(build_line(["IMU", "12", "0.98"]))
        port.write(b"$IMU,13,0.97*00\n")  # wrong checksum
        port.write(b"noise\n")
        port.write(build_line(["IMU", "14", "0.99"]))
        port.write(b"$IMU,15")  # partial line, rest never arrives
        lines, bad = read_lines(port, 10)
        print("valid:", lines, "bad:", bad)
    finally:
        port.close()

    calls = {"n": 0}

    def flaky_open() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise serial.SerialException("device busy")
        return "port-open"

    print(open_with_retry(flaky_open, sleep=lambda _s: None), "after", calls["n"], "tries")

    db = load_db()
    channel = f"demo-{uuid.uuid4().hex[:8]}"
    ecu = can.Bus(interface="virtual", channel=channel)
    motor = can.Bus(
        interface="virtual", channel=channel, can_filters=[{"can_id": 0x100, "can_mask": 0x7FF}]
    )
    try:
        ecu.send(encode_can(db, "MotorCmd", {"Speed": 1500.5, "Enable": 1, "Temp": -5}))
        ecu.send(
            can.Message(arbitration_id=0x7FF, data=b"\x01", is_extended_id=False)
        )  # filtered out
        print("motor node got:", collect(motor, db, 2))
        motor.send(encode_can(db, "Heartbeat", {"Counter": 1, "State": 2}))
        print("ECU saw:", collect(ecu, db, 2))  # one frame, then a quiet timeout
    finally:
        ecu.shutdown()
        motor.shutdown()


if __name__ == "__main__":
    run_demo()
