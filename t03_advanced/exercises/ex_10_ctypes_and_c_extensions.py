"""Exercise 10: ctypes, struct and buffers.

Tasks
1. pack_header / unpack_header: a binary header (version: u8, flags: u8, length: u16),
   network byte order, using `struct`.
2. make_point: build a `ctypes.Structure` instance with int32 fields x and y.
3. make_int_array: build a C array of int32 from a list and return it.
4. zero_copy_window: slice a bytearray with a memoryview (no copy) so writes go through.
5. libc_strlen: call the C library's strlen through ctypes (set argtypes/restype).

Run: uv run pytest t03_advanced -k ctypes
"""

from typing import Any


def pack_header(version: int, flags: int, length: int) -> bytes:
    """Pack into 4 bytes: version (u8), flags (u8), length (u16), big-endian / network order."""
    raise NotImplementedError


def unpack_header(data: bytes) -> tuple[int, int, int]:
    """Inverse of pack_header: return (version, flags, length)."""
    raise NotImplementedError


def make_point(x: int, y: int) -> Any:
    """Return a ctypes.Structure instance with c_int32 fields `x` and `y` (8 bytes total).

    Define the Structure subclass yourself (inside or outside this function).
    """
    raise NotImplementedError


def make_int_array(values: list[int]) -> Any:
    """Return a ctypes array of c_int32 containing `values` (len(result) == len(values))."""
    raise NotImplementedError


def zero_copy_window(buf: bytearray, start: int, stop: int) -> memoryview:
    """Return a memoryview of buf[start:stop] that shares memory with `buf` (no copy)."""
    raise NotImplementedError


def libc_strlen(text: bytes) -> int:
    """Call libc's strlen on `text` via ctypes and return the result.

    Use ctypes.util.find_library("c") (fall back to ctypes.CDLL(None)), and declare
    argtypes=[c_char_p] and restype=c_size_t.
    """
    raise NotImplementedError
