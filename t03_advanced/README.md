# Track 03 — Advanced Python

**Who it's for:** Experienced Python developers moving toward senior, library, or platform-level work

## Goals

- Write typed, extensible code with protocols, generics, and descriptors
- Choose the right concurrency model (threads, processes, asyncio) and measure it
- Profile, optimize, and expose clean CLIs and validated data models

## Prerequisite tracks

- t01_fundamentals, t02_intermediate

## Setup

```bash
uv sync
```

Note: Stdlib only, except the pydantic and typer lessons (07, 08), which need `uv add pydantic typer`.

## Lessons

| File | Topic | Status |
|---|---|---|
| `m_01_protocols_abcs_generics.py` | Protocols, ABCs and Generics | STUB |
| `m_02_descriptors_metaclasses.py` | Descriptors and Metaclasses | STUB |
| `m_03_functools_itertools.py` | functools and itertools in Practice | STUB |
| `m_04_threading_multiprocessing_gil.py` | Threads, Processes and the GIL | STUB |
| `m_05_asyncio_deep_dive.py` | asyncio Deep Dive | STUB |
| `m_06_profiling_performance.py` | Profiling and Performance | STUB |
| `m_07_pydantic_v2.py` | Pydantic v2 | STUB |
| `m_08_cli_with_typer.py` | Command-Line Apps with Typer | STUB |
| `m_09_design_patterns.py` | Design Patterns in Idiomatic Python | STUB |
| `m_10_ctypes_and_c_extensions.py` | ctypes and C Extensions | STUB |

## Checklist

- [ ] m_01: Protocols, ABCs and Generics
- [ ] m_02: Descriptors and Metaclasses
- [ ] m_03: functools and itertools in Practice
- [ ] m_04: Threads, Processes and the GIL
- [ ] m_05: asyncio Deep Dive
- [ ] m_06: Profiling and Performance
- [ ] m_07: Pydantic v2
- [ ] m_08: Command-Line Apps with Typer
- [ ] m_09: Design Patterns in Idiomatic Python
- [ ] m_10: ctypes and C Extensions

## Capstone project

Build a typed, concurrent command-line tool that loads a folder of JSON records, validates them with Pydantic models, and processes them in parallel using a process pool. Requirements: Protocol-based pluggable processors, a functools-cached lookup step, asyncio-based fetching of optional remote data with timeouts, a Typer CLI with subcommands, and a cProfile/tracemalloc report that shows the speedup over the serial version. Include a short design-notes section explaining which patterns were used and why.
