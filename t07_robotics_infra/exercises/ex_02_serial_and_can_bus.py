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


def load_db() -> Any:
    return cantools.database.load_string(DBC, database_format="dbc")


def nmea_checksum(body: str) -> str:
    """Two-digit uppercase hex XOR of the ASCII bytes of `body`. nmea_checksum("A") == "41"."""
    raise NotImplementedError


def build_line(fields: list[str]) -> bytes:
    """b"$" + ",".join(fields) + b"*" + checksum + b"\n" (checksum over the joined body)."""
    raise NotImplementedError


def parse_line(line: bytes) -> list[str]:
    """Validate and split one line; return the list of fields.

    ValueError if it does not start with `$`, has no `*`, or the checksum is wrong
    (accept lowercase hex digits). Trailing whitespace/newline is ignored.
    """
    raise NotImplementedError


def read_lines(port: serial.SerialBase, max_lines: int) -> tuple[list[list[str]], int]:
    """Read up to `max_lines` VALID lines from `port` using port.read_until(b"\n").

    Return (lines, bad_count). A line that fails parse_line counts as bad and is skipped.
    Stop as soon as a read does not end with a newline (timeout or partial line).
    """
    raise NotImplementedError


def open_with_retry[T](
    opener: Callable[[], T],
    attempts: int = 5,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call opener() until it returns. On OSError / serial.SerialException wait
    min(max_delay, base_delay * 2**attempt) via sleep(delay) and try again.

    After `attempts` failed calls re-raise the LAST exception without sleeping again.
    Any other exception type propagates immediately.
    """
    raise NotImplementedError


def encode_can(db: Any, name: str, signals: dict[str, float]) -> can.Message:
    """Encode `signals` for DBC message `name` into a standard-id can.Message
    (arbitration_id = the message frame id, is_extended_id=False)."""
    raise NotImplementedError


def decode_can(db: Any, msg: can.Message) -> tuple[str, dict[str, Any]] | None:
    """Return (message_name, signals) or None when the arbitration id is not in the DBC."""
    raise NotImplementedError


def collect(bus: can.BusABC, db: Any, count: int, timeout: float = 0.2) -> list[tuple[str, Any]]:
    """Call bus.recv(timeout=timeout) repeatedly, returning decoded (name, signals) pairs.

    Frames unknown to the DBC are skipped. Stop when `count` frames are decoded or when
    recv returns None (silence).
    """
    raise NotImplementedError
