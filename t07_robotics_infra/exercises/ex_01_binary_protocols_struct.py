"""Exercise 01: binary protocols with struct.

Wire format (all little-endian)
- Sample record, 21 bytes: `<IHhB3f` = ts_ms u32, battery_mv u16, temp_x10 i16, flags u8,
  accel x/y/z f32.
- Frame: SYNC(0xA5) u8, msg_type u8, payload_len u16, payload, crc u16.
  The CRC is CRC-16/CCITT-FALSE over msg_type + payload_len + payload (NOT the sync byte).

Tasks
1. crc16_ccitt: poly 0x1021, init 0xFFFF, no reflection, no final xor. check("123456789") = 0x29B1.
2. pack_sample / unpack_sample: temperature is sent as round(temp_c * 10).
3. encode_frame / decode_frame: build and parse ONE complete frame (ValueError when invalid).
4. FrameDecoder: incremental decoder for a byte stream that survives garbage and bad CRCs.
5. cobs_encode / cobs_decode: Consistent Overhead Byte Stuffing (output never contains 0x00).

Run: uv run pytest t07_robotics_infra -k binary_protocols
"""

import struct  # noqa: F401  (handy for tasks 2 and 3)
from typing import Any

SYNC = 0xA5
MAX_PAYLOAD = 256
SAMPLE = struct.Struct("<IHhB3f")


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE. `crc` is the running value so calls can be chained."""
    raise NotImplementedError


def pack_sample(
    ts_ms: int, battery_mv: int, temp_c: float, flags: int, accel: tuple[float, float, float]
) -> bytes:
    """Pack a telemetry sample into 21 bytes (see SAMPLE)."""
    raise NotImplementedError


def unpack_sample(data: bytes) -> dict[str, Any]:
    """Inverse of pack_sample. Keys: ts_ms, battery_mv, temp_c (float, = temp_x10 / 10),
    flags, accel (tuple of 3 floats). Raise ValueError if `len(data)` is not 21.
    """
    raise NotImplementedError


def encode_frame(msg_type: int, payload: bytes) -> bytes:
    """Return SYNC | type | len | payload | crc. ValueError if payload > MAX_PAYLOAD."""
    raise NotImplementedError


def decode_frame(data: bytes) -> tuple[int, bytes]:
    """Parse exactly one frame that fills `data`; return (msg_type, payload).

    ValueError for: too short, wrong SYNC, length field not matching len(data), bad CRC.
    """
    raise NotImplementedError


class FrameDecoder:
    """Incremental stream decoder.

    - feed(chunk) accepts ANY chunking (even 1 byte at a time) and returns the list of
      (msg_type, payload) frames completed by this chunk, in order.
    - Bytes before a SYNC are garbage: skip them (count in `dropped_bytes`).
    - A frame whose length > MAX_PAYLOAD or whose CRC is wrong increments `bad_frames`; drop
      ONE byte (the false SYNC) and resync, so a valid frame hidden inside is still found.
    - Never block waiting for a frame that is incomplete: just return and keep the bytes.
    """

    def __init__(self) -> None:
        self.bad_frames = 0
        self.dropped_bytes = 0

    def feed(self, chunk: bytes) -> list[tuple[int, bytes]]:
        raise NotImplementedError


def cobs_encode(data: bytes) -> bytes:
    """COBS-encode `data`. Does NOT append the 0x00 delimiter. cobs_encode(b"") == b"\\x01"."""
    raise NotImplementedError


def cobs_decode(data: bytes) -> bytes:
    """Inverse of cobs_encode. ValueError on a 0x00 byte inside `data` or a block that runs
    past the end.
    """
    raise NotImplementedError
