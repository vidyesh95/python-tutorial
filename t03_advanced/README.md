# Track 03: Advanced Python

Goal: move from "I write correct Python" to "I design and ship Python that other engineers
build on". By the end you will type and structure extensible code (protocols, generics,
descriptors), pick the right concurrency model (threads, processes, asyncio) and measure the
result, validate data with Pydantic, ship a CLI with Typer, recognise the design patterns that
show up in real backend, ML and robotics codebases, and know how Python talks to C.

Prerequisites: `t01_fundamentals` and `t02_intermediate`. Python 3.13, managed with `uv`.
Only the standard library, pytest, pydantic v2 and typer are needed (all installed by
`uv sync`).

## Lessons

| #  | Lesson (`m_NN_*.py`)             | You learn                                                                 |
|----|----------------------------------|---------------------------------------------------------------------------|
| 01 | `m_01_protocols_abcs_generics`   | `Protocol`, `ABC`, PEP 695 generics, `runtime_checkable`                   |
| 02 | `m_02_descriptors_metaclasses`   | `__get__/__set__/__set_name__`, `type()`, metaclasses, `__init_subclass__` |
| 03 | `m_03_functools_itertools`       | `cache`, `partial`, `singledispatch`, `reduce`, itertools recipes          |
| 04 | `m_04_threading_multiprocessing_gil` | the GIL, threads for I/O, process pools for CPU, locks, queues, free-threaded 3.13t |
| 05 | `m_05_asyncio_deep_dive`         | event loop, tasks, `TaskGroup`, timeouts, semaphores, queues, cancellation |
| 06 | `m_06_profiling_performance`     | `timeit`, `cProfile`, `tracemalloc`, `__slots__`, algorithmic wins         |
| 07 | `m_07_pydantic_v2`               | `BaseModel`, `Field`, validators, `computed_field`, `TypeAdapter`          |
| 08 | `m_08_cli_with_typer`            | Typer apps, options, subcommands, testing with `CliRunner`                 |
| 09 | `m_09_design_patterns`           | strategy, factory, adapter, observer, repository, dependency injection     |
| 10 | `m_10_ctypes_and_c_extensions`   | `ctypes`, `struct`, `array`, `memoryview`, cffi/Cython/pybind11/PyO3       |

Status: all ten lessons are complete (✅).

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`.

## How to work

1. Run the lesson and read the code next to its output.
2. Open the exercise, read the docstrings, implement the stubs.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t03_advanced.m_05_asyncio_deep_dive
```

Lessons need no input or network and leave no files behind. Lesson 04 uses a process pool, so
always run it as a module (`-m`) or as a script, never paste it into a REPL.

### Run the tests

```bash
uv run pytest t03_advanced                    # all exercises (fail until you implement them)
uv run pytest t03_advanced -k asyncio         # one exercise by keyword
uv run pytest t03_advanced -x                 # stop at the first failure
SOLUTIONS=1 uv run pytest t03_advanced        # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t03_advanced && uv run ruff format t03_advanced
```

## Progress checklist

- [ ] 01 Protocols, ABCs and generics: lesson read, exercise passing
- [ ] 02 Descriptors and metaclasses: lesson read, exercise passing
- [ ] 03 functools and itertools: lesson read, exercise passing
- [ ] 04 Threads, processes and the GIL: lesson read, exercise passing
- [ ] 05 asyncio deep dive: lesson read, exercise passing
- [ ] 06 Profiling and performance: lesson read, exercise passing
- [ ] 07 Pydantic v2: lesson read, exercise passing
- [ ] 08 CLI apps with Typer: lesson read, exercise passing
- [ ] 09 Design patterns: lesson read, exercise passing
- [ ] 10 ctypes and C extensions: lesson read, exercise passing
- [ ] Capstone below finished and tested
- [ ] `uv run ruff check t03_advanced` is clean

## Capstone: concurrent link checker CLI

Build `linkcheck`, a typed command line tool that checks many URLs concurrently with
bounded concurrency and polite rate limiting. Put it in its own folder (for example
`capstone_t03/`). To stay offline-friendly, hide the network behind a `Fetcher` protocol and
test with a fake fetcher; a real implementation can use `urllib` via `asyncio.to_thread`, or
`httpx` if you add it.

Requirements

1. **Models (Pydantic v2)**: `CheckRequest` (validated URL string, `timeout` with
   `Field(gt=0)`) and `CheckResult` (`url`, `status`, `elapsed_ms`, `error`, plus a
   `computed_field` such as `ok`). Use a `TypeAdapter` to load a list of requests from JSON.
2. **Protocols and generics**: a `Fetcher` `Protocol` (`async def fetch(url) -> Response`),
   a generic `Result[T]` or `Ok/Err` type, and an `ABC` for output formatters
   (table, JSON).
3. **Concurrency (asyncio)**: run checks in an `asyncio.TaskGroup` with an
   `asyncio.Semaphore` for max in-flight requests, `asyncio.timeout` per request, and a
   token-bucket rate limiter (requests per second). Use an `asyncio.Queue` producer/consumer
   if you want to discover links from pages. Cancellation must clean up promptly.
4. **Patterns**: strategy for the retry/backoff policy, observer (callbacks or an event
   list) for progress reporting, dependency injection of the fetcher and clock into the
   service, and a repository that stores results (in memory first, SQLite or a JSON file
   later).
5. **functools / itertools**: `functools.cache` for URL normalisation, `itertools.batched`
   for chunking input, `singledispatch` for rendering results.
6. **CLI (Typer)**: `linkcheck run URLS.json --concurrency 10 --rate 5 --timeout 3
   --format table|json` and `linkcheck version`. Exit code 1 if any URL failed.
7. **Performance**: use `timeit` or `cProfile` to compare serial vs concurrent runs against
   the fake fetcher (which sleeps briefly), and `tracemalloc` to confirm memory stays flat
   for a large input. Record the numbers in a short design-notes section.
8. **Tests (pytest)**: fake fetcher and fake clock, `asyncio.run` inside sync tests (or
   `pytest-asyncio` if you add it), `CliRunner` for the CLI, tests for timeouts, rate
   limiting (never exceeds N per second) and cancellation.

Stretch: add a `ProcessPoolExecutor` stage that parses large HTML bodies for links, and
compare with a thread pool on a GIL build versus `python3.13t`.
