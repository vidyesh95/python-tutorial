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

import struct
from typing import Any

SYNC = 0xA5
HEADER = struct.Struct("<BBH")
CRC = struct.Struct("<H")
MAX_PAYLOAD = 256
SAMPLE = struct.Struct("<IHhB3f")


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def pack_sample(
    ts_ms: int, battery_mv: int, temp_c: float, flags: int, accel: tuple[float, float, float]
) -> bytes:
    """Pack a telemetry sample into 21 bytes (see SAMPLE)."""
    return SAMPLE.pack(ts_ms, battery_mv, round(temp_c * 10), flags, *accel)


def unpack_sample(data: bytes) -> dict[str, Any]:
    """Inverse of pack_sample. Keys: ts_ms, battery_mv, temp_c (float, = temp_x10 / 10),
    flags, accel (tuple of 3 floats). Raise ValueError if `len(data)` is not 21.
    """
    if len(data) != SAMPLE.size:
        raise ValueError(f"expected {SAMPLE.size} bytes, got {len(data)}")
    ts, mv, t10, flags, ax, ay, az = SAMPLE.unpack(data)
    return {
        "ts_ms": ts,
        "battery_mv": mv,
        "temp_c": t10 / 10,
        "flags": flags,
        "accel": (ax, ay, az),
    }


def encode_frame(msg_type: int, payload: bytes) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    head = HEADER.pack(SYNC, msg_type, len(payload))
    return head + payload + CRC.pack(crc16_ccitt(head[1:] + payload))


def decode_frame(data: bytes) -> tuple[int, bytes]:
    """Parse exactly one frame that fills `data`; return (msg_type, payload).

    ValueError for: too short, wrong SYNC, length field not matching len(data), bad CRC.
    """
    if len(data) < HEADER.size + CRC.size:
        raise ValueError("frame too short")
    sync, msg_type, length = HEADER.unpack_from(data)
    if sync != SYNC:
        raise ValueError("bad sync")
    if len(data) != HEADER.size + length + CRC.size:
        raise ValueError("length mismatch")
    (crc,) = CRC.unpack_from(data, HEADER.size + length)
    if crc != crc16_ccitt(data[1 : HEADER.size + length]):
        raise ValueError("bad crc")
    return msg_type, bytes(data[HEADER.size : HEADER.size + length])


class FrameDecoder:
    """Incremental decoder: feed() any chunking of the stream, get complete frames back."""

    def __init__(self) -> None:
        self.buf = bytearray()
        self.bad_frames = 0
        self.dropped_bytes = 0

    def feed(self, chunk: bytes) -> list[tuple[int, bytes]]:
        self.buf += chunk
        frames: list[tuple[int, bytes]] = []
        while True:
            start = self.buf.find(SYNC)
            if start < 0:
                self.dropped_bytes += len(self.buf)
                self.buf.clear()
                break
            if start:
                self.dropped_bytes += start
                del self.buf[:start]
            if len(self.buf) < HEADER.size:
                break  # need more bytes
            _, msg_type, length = HEADER.unpack_from(self.buf)
            if length > MAX_PAYLOAD:  # corrupt length: do not wait for it
                self._resync()
                continue
            total = HEADER.size + length + CRC.size
            if len(self.buf) < total:
                break
            body = bytes(self.buf[1 : HEADER.size + length])
            (crc,) = CRC.unpack_from(self.buf, HEADER.size + length)
            if crc != crc16_ccitt(body):
                self._resync()
                continue
            frames.append((msg_type, bytes(self.buf[HEADER.size : HEADER.size + length])))
            del self.buf[:total]
        return frames

    def _resync(self) -> None:
        self.bad_frames += 1
        self.dropped_bytes += 1
        del self.buf[:1]  # drop the false SYNC and look for the next one


def cobs_encode(data: bytes) -> bytes:
    out = bytearray()
    block = bytearray()
    for byte in data:
        if byte == 0:
            out.append(len(block) + 1)
            out += block
            block.clear()
        else:
            block.append(byte)
            if len(block) == 254:
                out.append(255)
                out += block
                block.clear()
    out.append(len(block) + 1)
    out += block
    return bytes(out)


def cobs_decode(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        code = data[i]
        if code == 0 or i + code > len(data):
            raise ValueError("invalid COBS data")
        out += data[i + 1 : i + code]
        i += code
        if code < 255 and i < len(data):
            out.append(0)
    return bytes(out)
