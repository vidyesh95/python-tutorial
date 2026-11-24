# Binary Protocols with struct
"""
Robots, motor drivers and sensors talk in compact binary, not JSON: a 21-byte record
instead of 150 bytes of text, no parsing ambiguity, fixed cost per message. `struct` turns
Python values into bytes and back.

struct format strings
- The first character picks byte order AND alignment: `<` little-endian, `>` big-endian
  (network order), `=` native order without padding, `@` (default!) native order WITH
  alignment padding. For wire formats always write `<` or `>` explicitly.
- Codes: `B` u8, `b` i8, `H` u16, `h` i16, `I` u32, `i` i32, `Q` u64, `f` f32, `d` f64,
  `?` bool, `Ns` N raw bytes, `x` one pad byte. A count prefix repeats: `3f`.
- `calcsize` gives the byte size, `pack` / `unpack` work on whole buffers, `unpack_from`
  reads at an offset, `iter_unpack` walks an array of records, `Struct(fmt)` precompiles.

Endianness: 0x1234 is `34 12` little-endian (x86, ARM, most MCUs, CAN/Intel signals) and
`12 34` big-endian (network protocols, Motorola CAN signals). Both ends must agree.

Framing: a byte stream (serial, TCP) has no message boundaries, so add them.
- Length prefix: SYNC byte, type, length, payload, checksum. The decoder buffers bytes,
  finds SYNC, waits for `length` more bytes, verifies the checksum, emits the frame. After
  garbage or a bad checksum it drops ONE byte and searches for the next SYNC (resync).
- COBS (Consistent Overhead Byte Stuffing): rewrites the payload so it has no 0x00 byte;
  then 0x00 is a perfect frame delimiter and resync is trivial (read to the next 0x00).
  Overhead is at most 1 byte per 254.

Checksums detect corruption (they are not security): XOR/sum are cheap but weak, CRC-16 or
CRC-32 catch bursts and are standard. Here: CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF),
whose check value for b"123456789" is 0x29B1.

memoryview: slice a buffer without copying (`mv[4:10]`), and feed it to `unpack_from`.
Useful for high-rate streams where `bytes` slicing would allocate on every message.

Common mistakes
- Forgetting the byte-order prefix: `"IHh"` pads and uses native order, so the size and
  layout differ between machines. Always `"<IHh"`.
- Trusting the length field from the wire: cap it (MAX_PAYLOAD) or a corrupt length makes
  the decoder wait forever for bytes that never come.
- Assuming one `read()` equals one message. Reads return arbitrary chunks.
- Checksum computed over the wrong range (must cover type and length, not only payload).
- Using floats for exact values; send scaled integers (temperature x10 as i16) instead.

Production notes
- Version the protocol (a version byte or a type id per layout) so firmware and server can
  upgrade independently. Ignore unknown fields/types instead of crashing.
- Count and expose bad frames / dropped bytes as metrics; a rising rate means a bad cable.
- Never trust sensor data blindly: range-check every decoded value (NaN, absurd
  temperatures, time going backwards) before it drives control decisions.
- Add a sequence number so you can see lost frames; use a watchdog on the receiver so
  silence triggers a safe state (stop motors), not "keep the last command".
"""

import struct
from typing import Any

SYNC = 0xA5
HEADER = struct.Struct("<BBH")  # sync, msg_type, payload_len
CRC = struct.Struct("<H")
MAX_PAYLOAD = 256
SAMPLE = struct.Struct("<IHhB3f")  # ts_ms, battery_mv, temp_x10, flags, ax, ay, az


# Example 1: struct basics, byte order and padding
def struct_basics() -> None:
    print(
        "0x1234 little:", struct.pack("<H", 0x1234).hex(), "big:", struct.pack(">H", 0x1234).hex()
    )
    print("sizes: '<IHh' =", struct.calcsize("<IHh"), " native '@BI' =", struct.calcsize("@BI"))
    print("'<BI' =", struct.calcsize("<BI"), "(no padding on the wire)")
    print("unpack:", struct.unpack("<HhB", b"\x01\x00\xff\xff\x07"))


# Example 2: a fixed-layout telemetry record
def pack_sample(
    ts_ms: int, battery_mv: int, temp_c: float, flags: int, accel: tuple[float, float, float]
) -> bytes:
    return SAMPLE.pack(ts_ms, battery_mv, round(temp_c * 10), flags, *accel)


def unpack_sample(data: bytes) -> dict[str, Any]:
    ts, mv, t10, flags, ax, ay, az = SAMPLE.unpack(data)
    return {
        "ts_ms": ts,
        "battery_mv": mv,
        "temp_c": t10 / 10,
        "flags": flags,
        "accel": (ax, ay, az),
    }


# Example 3: checksums
def xor_checksum(data: bytes) -> int:
    out = 0
    for b in data:
        out ^= b
    return out


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


# Example 4: length-prefixed frames with a CRC
def encode_frame(msg_type: int, payload: bytes) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    head = HEADER.pack(SYNC, msg_type, len(payload))
    return head + payload + CRC.pack(crc16_ccitt(head[1:] + payload))


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


# Example 5: COBS framing (0x00 is the delimiter)
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


# Example 6: memoryview: walk an array of records without copying
def read_samples(buf: bytes) -> list[dict[str, Any]]:
    mv = memoryview(buf)
    usable = len(mv) - len(mv) % SAMPLE.size
    return [unpack_sample(bytes(mv[o : o + SAMPLE.size])) for o in range(0, usable, SAMPLE.size)]


def run_demo() -> None:
    struct_basics()
    print("crc16('123456789') =", hex(crc16_ccitt(b"123456789")), "xor =", xor_checksum(b"abc"))

    raw = pack_sample(1000, 12_400, 36.6, 0b101, (0.0, 0.1, 9.81))
    print(f"sample is {len(raw)} bytes ->", unpack_sample(raw))

    stream = encode_frame(1, raw) + b"\x00garbage" + encode_frame(2, b"ping")
    corrupted = bytearray(stream)
    corrupted[10] ^= 0xFF  # flip bits inside the first frame
    for name, data in (("clean", stream), ("corrupted", bytes(corrupted))):
        dec = FrameDecoder()
        frames = []
        for i in range(0, len(data), 7):  # arbitrary 7-byte chunks, like a serial port
            frames += dec.feed(data[i : i + 7])
        print(
            f"{name}: frames={[t for t, _ in frames]} bad={dec.bad_frames} dropped={dec.dropped_bytes}"
        )

    enc = cobs_encode(b"\x11\x00\x22\x00\x00")
    print("cobs:", enc.hex(), "->", cobs_decode(enc).hex(), "(no zeros inside:", 0 not in enc, ")")
    print("array of records:", len(read_samples(raw * 3)))


if __name__ == "__main__":
    run_demo()
