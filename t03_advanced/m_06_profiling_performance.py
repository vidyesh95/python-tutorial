# Profiling and Performance
"""
Rule one of performance work: MEASURE FIRST. Guessing where the time goes is wrong most of
the time. The workflow:
    1. Make it correct and write a test.
    2. Measure with a representative workload (timeit for snippets, cProfile for programs).
    3. Fix the biggest hotspot only. Usually that is an algorithm or data structure.
    4. Measure again. Stop when it is fast enough.

Tools covered here (all stdlib):
- timeit: micro-benchmarks. Use `repeat` and take the MIN (noise only ever adds time).
- cProfile + pstats: which functions consume time, and how often they are called.
- tracemalloc: which lines allocate memory, and peak usage.
- __slots__: smaller objects when you create millions of them.
- Algorithmic wins: set/dict lookups, sorted + bisect, avoiding repeated work.

Common mistakes:
- Optimizing without a profile ("this loop looks slow").
- Benchmarking once, or with the average instead of the min.
- Profiling tiny inputs: constant factors hide the real growth curve (O(n^2) vs O(n)).
- Micro-optimizing Python loops when a better algorithm or numpy would win 100x.
- Leaving cProfile on in production (it adds overhead; use sampling profilers there).

Where this shows up in backend/ML/robotics work:
- Backend: finding the N+1 query or the O(n^2) serializer behind a slow endpoint.
- ML: data-loading and preprocessing loops that starve the GPU; memory leaks in batches.
- Robotics: control loops with a hard per-tick time budget; allocation spikes causing jitter.
Sampling profilers worth knowing: py-spy, scalene. Memory: memray.
"""

import cProfile
import io
import pstats
import timeit
import tracemalloc
from bisect import bisect_left


# Example: timeit, comparing two ways to build a list
def squares_loop(n: int) -> list[int]:
    out = []
    for i in range(n):
        out.append(i * i)
    return out


def squares_comp(n: int) -> list[int]:
    return [i * i for i in range(n)]


# repeat(...) returns several totals; min() is the least-noisy estimate
loop_t = min(timeit.repeat(lambda: squares_loop(1000), number=200, repeat=3))
comp_t = min(timeit.repeat(lambda: squares_comp(1000), number=200, repeat=3))
print(f"loop {loop_t * 1000:.1f} ms vs comprehension {comp_t * 1000:.1f} ms (200 runs)")


# Example: algorithmic win, membership in list (O(n)) vs set (O(1))
haystack_list = list(range(5000))
haystack_set = set(haystack_list)
needles = list(range(4000, 4100))

t_list = min(timeit.repeat(lambda: [n in haystack_list for n in needles], number=5, repeat=3))
t_set = min(timeit.repeat(lambda: [n in haystack_set for n in needles], number=5, repeat=3))
print(f"set lookup is {t_list / t_set:.0f}x faster than list scan here")
print("set wins by >10x:", t_list / t_set > 10)

# bisect: O(log n) search in sorted data
print("bisect_left finds index:", bisect_left(haystack_list, 4242))


# Example: cProfile + pstats to find the hotspot
def slow_unique(items: list[int]) -> list[int]:
    seen: list[int] = []  # BUG-ish: list membership makes this O(n^2)
    for x in items:
        if x not in seen:
            seen.append(x)
    return seen


def fast_unique(items: list[int]) -> list[int]:
    return list(dict.fromkeys(items))  # O(n), keeps first-seen order


def workload() -> None:
    data = [i % 700 for i in range(4000)]
    slow_unique(data)
    fast_unique(data)


profiler = cProfile.Profile()
profiler.enable()
workload()
profiler.disable()

buffer = io.StringIO()
stats = pstats.Stats(profiler, stream=buffer).strip_dirs().sort_stats("cumulative")
stats.print_stats(5)
# print_stats output is long; show only the rows that name our functions
for line in buffer.getvalue().splitlines():
    if "unique" in line or "workload" in line:
        print("  profile:", " ".join(line.split()[:5]), line.split()[-1])
slow_row = next(v for k, v in stats.stats.items() if k[2] == "slow_unique")  # type: ignore[attr-defined]
print("slow_unique ncalls:", slow_row[0])  # row: (cc, nc, tottime, cumtime, callers)
print("same result:", slow_unique([3, 1, 3, 2]) == fast_unique([3, 1, 3, 2]))


# Example: tracemalloc, how much memory does a structure use?
def build_strings(n: int) -> list[str]:
    return [f"item-{i}" for i in range(n)]


tracemalloc.start()
data = build_strings(10_000)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print("tracemalloc saw allocations:", current > 100_000 and peak >= current)

tracemalloc.start()
before = tracemalloc.take_snapshot()
data2 = build_strings(5_000)
after = tracemalloc.take_snapshot()
top = after.compare_to(before, "lineno")[0]  # biggest allocation difference by source line
print(
    "top allocation site is in this file:",
    top.traceback[0].filename.endswith("m_06_profiling_performance.py"),
)
tracemalloc.stop()


# Example: __slots__ shrinks per-instance memory (no per-object __dict__)
class PointDict:
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y


class PointSlots:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y


def measure(cls: type, n: int = 5_000) -> int:
    tracemalloc.start()
    objs = [cls(1.0, 2.0) for _ in range(n)]
    size, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del objs
    return size


dict_size, slots_size = measure(PointDict), measure(PointSlots)
print("slots use less memory:", slots_size < dict_size)
print("PointSlots has __dict__:", hasattr(PointSlots(1, 2), "__dict__"))

# Example: avoid repeated work, hoist invariants and use join instead of += in loops
parts = [str(i) for i in range(2000)]
joined = ",".join(parts)  # O(n); repeated `s += p` can degrade to O(n^2) on other interpreters
print("joined length:", len(joined))
