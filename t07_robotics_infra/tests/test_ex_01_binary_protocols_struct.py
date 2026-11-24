import random
import struct

import pytest

from _loader import load

ex = load("t07_robotics_infra", "ex_01_binary_protocols_struct")


def test_crc16_check_value_and_chaining():
    assert ex.crc16_ccitt(b"123456789") == 0x29B1
    assert ex.crc16_ccitt(b"") == 0xFFFF
    assert ex.crc16_ccitt(b"6789", ex.crc16_ccitt(b"12345")) == 0x29B1


def test_sample_roundtrip_and_size():
    raw = ex.pack_sample(123456, 12400, 36.6, 5, (0.5, -1.25, 9.75))
    assert len(raw) == 21
    assert raw[:4] == struct.pack("<I", 123456)  # little-endian
    out = ex.unpack_sample(raw)
    assert out == {
        "ts_ms": 123456,
        "battery_mv": 12400,
        "temp_c": 36.6,
        "flags": 5,
        "accel": (0.5, -1.25, 9.75),
    }


def test_sample_negative_temperature_and_bad_length():
    assert ex.unpack_sample(ex.pack_sample(1, 1, -12.3, 0, (0, 0, 0)))["temp_c"] == -12.3
    with pytest.raises(ValueError):
        ex.unpack_sample(b"\x00" * 20)


def test_encode_frame_layout():
    frame = ex.encode_frame(7, b"abc")
    assert frame[:4] == bytes([0xA5, 7, 3, 0])
    assert frame[4:7] == b"abc"
    assert struct.unpack("<H", frame[7:])[0] == ex.crc16_ccitt(bytes([7, 3, 0]) + b"abc")
    with pytest.raises(ValueError):
        ex.encode_frame(1, b"x" * (ex.MAX_PAYLOAD + 1))


def test_decode_frame_roundtrip_and_errors():
    frame = ex.encode_frame(9, b"hello")
    assert ex.decode_frame(frame) == (9, b"hello")
    assert ex.decode_frame(ex.encode_frame(1, b"")) == (1, b"")
    bad_crc = bytearray(frame)
    bad_crc[-1] ^= 1
    bad_sync = b"\x00" + frame[1:]
    for broken in (bytes(bad_crc), bad_sync, frame[:-1], frame + b"\x00", b"\xa5"):
        with pytest.raises(ValueError):
            ex.decode_frame(broken)


def test_decoder_handles_any_chunking():
    frames = [(1, b"one"), (2, b""), (3, bytes(range(200)))]
    stream = b"".join(ex.encode_frame(t, p) for t, p in frames)
    for size in (1, 2, 5, len(stream)):
        dec = ex.FrameDecoder()
        got = []
        for i in range(0, len(stream), size):
            got += dec.feed(stream[i : i + size])
        assert got == frames
        assert dec.bad_frames == 0 and dec.dropped_bytes == 0


def test_decoder_skips_garbage_and_counts_it():
    dec = ex.FrameDecoder()
    got = dec.feed(b"\x01\x02\x03" + ex.encode_frame(4, b"ok"))
    assert got == [(4, b"ok")]
    assert dec.dropped_bytes == 3


def test_decoder_resyncs_after_bad_crc_and_keeps_following_frame():
    good = ex.encode_frame(2, b"after")
    broken = bytearray(ex.encode_frame(1, b"before"))
    broken[5] ^= 0xFF
    dec = ex.FrameDecoder()
    assert dec.feed(bytes(broken) + good) == [(2, b"after")]
    assert dec.bad_frames >= 1


def test_decoder_finds_frame_hidden_inside_false_sync():
    inner = ex.encode_frame(5, b"inner")
    dec = ex.FrameDecoder()
    # a SYNC byte followed by a header that claims a short payload, fails the CRC and overlaps the real frame
    got = dec.feed(bytes([0xA5, 9, 3, 0]) + inner)
    assert got == [(5, b"inner")]


def test_decoder_rejects_oversized_length_without_waiting():
    dec = ex.FrameDecoder()
    assert dec.feed(bytes([0xA5, 1, 0xFF, 0xFF])) == []
    assert dec.bad_frames == 1
    assert dec.feed(ex.encode_frame(3, b"x")) == [(3, b"x")]


def test_cobs_known_vectors():
    assert ex.cobs_encode(b"") == b"\x01"
    assert ex.cobs_encode(b"\x00") == b"\x01\x01"
    assert ex.cobs_encode(b"\x11\x22\x00\x33") == b"\x03\x11\x22\x02\x33"
    assert ex.cobs_encode(b"\x11\x00\x22\x00\x00") == bytes.fromhex("021102220101")


def test_cobs_roundtrip_random_and_never_emits_zero():
    rng = random.Random(7)
    samples = [
        bytes(rng.choice([0, 1, 2, 255]) for _ in range(rng.randrange(0, 60))) for _ in range(50)
    ]
    samples += [
        b"\x05" * 253,
        b"\x05" * 254,
        b"\x05" * 255,
        b"\x05" * 600,
        bytes(range(1, 256)) * 2,
    ]
    for data in samples:
        enc = ex.cobs_encode(data)
        assert 0 not in enc
        assert ex.cobs_decode(enc) == data


def test_cobs_decode_rejects_invalid():
    with pytest.raises(ValueError):
        ex.cobs_decode(b"\x03\x11")  # block runs past the end
    with pytest.raises(ValueError):
        ex.cobs_decode(b"\x02\x11\x00\x01")  # zero inside
