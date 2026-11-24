import ctypes
import ctypes.util

import pytest

from _loader import load

ex = load("t03_advanced", "ex_10_ctypes_and_c_extensions")


def test_pack_header_layout():
    data = ex.pack_header(1, 2, 0x0304)
    assert isinstance(data, bytes)
    assert data == b"\x01\x02\x03\x04"


def test_unpack_header_roundtrip():
    assert ex.unpack_header(ex.pack_header(7, 255, 65535)) == (7, 255, 65535)


def test_make_point():
    p = ex.make_point(3, -4)
    assert isinstance(p, ctypes.Structure)
    assert (p.x, p.y) == (3, -4)
    assert ctypes.sizeof(p) == 8
    assert bytes(p)[:4] == (3).to_bytes(4, "little", signed=True)


def test_make_int_array():
    arr = ex.make_int_array([5, 6, 7])
    assert len(arr) == 3
    assert list(arr) == [5, 6, 7]
    assert ctypes.sizeof(arr) == 12


def test_zero_copy_window_shares_memory():
    buf = bytearray(b"abcdef")
    view = ex.zero_copy_window(buf, 2, 5)
    assert isinstance(view, memoryview)
    assert bytes(view) == b"cde"
    view[0] = ord("X")
    assert buf == bytearray(b"abXdef")
    view.release()


def _libc_available() -> bool:
    try:
        ctypes.CDLL(ctypes.util.find_library("c"))["strlen"]
    except OSError, TypeError, AttributeError, KeyError:
        return False
    return True


@pytest.mark.skipif(not _libc_available(), reason="libc with strlen not loadable here")
def test_libc_strlen():
    assert ex.libc_strlen(b"hello") == 5
    assert ex.libc_strlen(b"") == 0
    assert ex.libc_strlen(b"robotics") == 8
