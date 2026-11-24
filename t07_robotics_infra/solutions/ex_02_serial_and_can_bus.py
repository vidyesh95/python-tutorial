"""Exercise 02: serial lines, reconnect logic and CAN signals.

Text protocol: `$f1,f2,...*CC\n` where CC is the two-digit UPPERCASE hex XOR of every byte
between `$` and `*`. Ports are pyserial ports (tests use `serial_for_url("loop://")`);
CAN buses are python-can buses (tests use `interface="virtual"`); `db` is a cantools
database (use `load_db()`, provided below, with messages MotorCmd id 0x100 and Heartbeat 0x200).

Tasks
1. nmea_checksum / build_line / parse_line: build and validate checksummed lines.
2. read_lines: read valid lines from a port, count bad ones, stop at a timeout.
3. open_with_retry: retry an opener with exponential backoff (injectable sleep).
4. encode_can / decode_can: DBC signals <-> can.Message.
5. collect: receive and decode frames from a bus until `count` decoded or silence.

Run: uv run pytest t07_robotics_infra -k serial_and_can
"""

import time
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
