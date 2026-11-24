# ctypes and C Extensions
"""
Python can call C code, and most of the fast Python ecosystem (NumPy, PyTorch, OpenCV,
pydantic-core, orjson) does exactly that. This lesson covers the zero-dependency route
and maps out the others.

ctypes (stdlib): load a shared library at runtime and call it, no compiler needed.
- ctypes.util.find_library("c") locates a library by short name (None if missing).
- Always set `.argtypes` and `.restype`; the default assumes C `int` and will truncate
  pointers or doubles silently.
- ctypes.Structure mirrors a C struct; `c_int * 4` creates a C array type.
- Python owns the memory you allocate; C never frees it for you.

struct / array / memoryview: no library needed, just binary layout.
- struct packs and unpacks fixed binary layouts (network headers, file formats).
- array.array stores typed numbers compactly; memoryview slices buffers without copying.

Other ways to reach native code (overview, not run here):
- C-API / extension modules: the original; manual refcounting, maximum control.
- cffi: parse C declarations, ABI mode (like ctypes) or API mode (compiled, faster).
- Cython: Python-like syntax with C types, compiled to C. Great for numeric loops.
- pybind11 / nanobind: C++ bindings with templates; common for robotics and ML code.
- PyO3 (+ maturin): write extensions in Rust; safe and increasingly popular.
"""

import array
import ctypes
import ctypes.util
import struct


# Example: call libc through ctypes, with a graceful fallback
def load_libc() -> ctypes.CDLL | None:
    name = ctypes.util.find_library("c")
    candidates = [name] if name else []
    candidates.append(None)  # CDLL(None) = the current process (POSIX only)
    for candidate in candidates:
        try:
            return ctypes.CDLL(candidate)
        except OSError, TypeError:
            continue
    return None


libc = load_libc()
if libc is not None and hasattr(libc, "strlen"):
    libc.strlen.argtypes = [ctypes.c_char_p]
    libc.strlen.restype = ctypes.c_size_t
    print("libc strlen(b'hello'):", libc.strlen(b"hello"))
else:
    print("libc not available here; skipping the native call, using len():", len(b"hello"))

# Example: wrong vs right declarations (why argtypes/restype matter)
libm_name = ctypes.util.find_library("m")
if libm_name:
    try:
        libm = ctypes.CDLL(libm_name)
        libm.sqrt.argtypes = [ctypes.c_double]
        libm.sqrt.restype = ctypes.c_double
        print("libm sqrt(2.0):", round(libm.sqrt(2.0), 6))
    except OSError, AttributeError:
        print("libm could not be loaded; skipping")
else:
    print("libm not found; skipping")


# Example: C types, arrays and Structures need no library at all
class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


p = Point(3, 4)
print("Point:", p.x, p.y, "size:", ctypes.sizeof(p), "bytes")

IntArray4 = ctypes.c_int32 * 4
arr = IntArray4(10, 20, 30, 40)
print("c array:", list(arr), "len:", len(arr), "sizeof:", ctypes.sizeof(arr))

# Structures expose raw bytes: handy for binary protocols and C interop
raw = bytes(p)
print("raw bytes of Point:", raw.hex())
print("round-trip:", Point.from_buffer_copy(raw).x)


# Example: struct packs binary layouts (byte order is explicit: ! = network/big-endian)
packed = struct.pack("!BHI", 1, 513, 70000)
print("packed:", packed.hex(), "size:", struct.calcsize("!BHI"))
print("unpacked:", struct.unpack("!BHI", packed))


# Example: array.array + memoryview, zero-copy slicing of typed buffers
samples = array.array("h", [0, 100, -100, 200, -200, 300])  # signed 16-bit ints
view = memoryview(samples)
print("itemsize:", view.itemsize, "bytes total:", view.nbytes)
window = view[1:4]  # no copy
window[0] = 999  # writes through to the original array
print("after write through view:", samples.tolist())
print("as raw bytes (first 4):", view.cast("B")[:4].hex())

# bytearray + memoryview: fill a buffer in place (what recv_into / readinto do)
buf = bytearray(8)
mv = memoryview(buf)
struct.pack_into("<HH", mv, 0, 1, 2)
print("pack_into:", buf.hex(), "unpacked:", struct.unpack_from("<HH", buf, 0))

# Example: the cost of crossing the boundary
# Each ctypes call has overhead (~100s of ns), so call C once with a big buffer,
# not a million times with single values.

"""
Common mistakes
- Forgetting argtypes/restype: pointers get truncated to 32 bits, doubles come back as garbage.
- Passing a Python str where C expects bytes (use b"..." or .encode()).
- Keeping a pointer to a buffer after the Python object owning it was garbage collected.
- Hard-coding library names or paths; use find_library and handle None.
- Ignoring byte order and alignment in struct; "<" and "!" are explicit, native "@" pads.
- Reaching for ctypes when a pure-Python or NumPy solution is already fast enough.

Where this shows up in backend/ML/robotics work
- Backend: calling a vendor's C SDK, libc/libssl functions, or reading binary network headers.
- ML: NumPy/PyTorch tensors expose raw memory via the buffer protocol; ctypes/cffi wrap
  custom CUDA or C++ kernels; Cython/pybind11 speed up preprocessing.
- Robotics: sensor drivers and ROS libraries are C++ with Python bindings; binary logs
  (MCAP, serial packets, CAN frames) are parsed with struct and memoryview.
"""
