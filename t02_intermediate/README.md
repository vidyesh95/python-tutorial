# Track 02: Intermediate Python

Goal: move from "I can write scripts" to "I can read and write the Python used in real
backend and ML codebases". By the end you will be comfortable with Python's data-model hooks
(classes, dunders, dataclasses, enums), its lazy-evaluation tools (generators, context
managers), the patterns frameworks like FastAPI are built on (decorators, type hints), and
the everyday engineering skills around them (logging, testing, packaging, pathlib/json/csv,
datetimes, regex).

Prerequisite: `t01_fundamentals`. Python 3.13, managed with `uv`. Only the standard library
and pytest are needed.

## Lessons

| #  | Lesson (`m_NN_*.py`)        | You learn                                                         |
|----|-----------------------------|-------------------------------------------------------------------|
| 01 | `m_01_comprehensions`       | list/dict/set comprehensions, generator expressions               |
| 02 | `m_02_args_kwargs`          | `*args`, `**kwargs`, keyword-only, positional-only, unpacking     |
| 03 | `m_03_lambda_map_filter`    | lambda, map/filter, `sorted(key=)`, `functools.reduce`            |
| 04 | `m_04_classes_objects`      | attributes, methods, classmethod/staticmethod, property           |
| 05 | `m_05_inheritance_composition` | `super()`, MRO, mixins, composition over inheritance           |
| 06 | `m_06_dunder_methods`       | `__repr__`, `__eq__`, `__lt__`, `__len__`, `__iter__`, `__hash__`  |
| 07 | `m_07_dataclasses`          | `field`, frozen, slots, `__post_init__`, ordering                 |
| 08 | `m_08_enums`                | Enum, IntEnum, StrEnum, `auto`, `match`                           |
| 09 | `m_09_iterators_generators` | iterator protocol, `yield`, `yield from`, pipelines               |
| 10 | `m_10_decorators`           | `functools.wraps`, decorator factories, class decorators, retry   |
| 11 | `m_11_context_managers`     | `with`, `__enter__/__exit__`, `contextmanager`, `ExitStack`       |
| 12 | `m_12_type_hints`           | PEP 695 generics, TypedDict, Protocol, Literal, mypy/pyright      |
| 13 | `m_13_pathlib_json_csv`     | `Path`, reading/writing JSON and CSV safely                       |
| 14 | `m_14_logging`              | levels, handlers, formatters, structured logging                  |
| 15 | `m_15_datetime`             | aware datetimes, `zoneinfo`, `timedelta`, ISO 8601                |
| 16 | `m_16_regex`                | `re`, groups, named groups, `sub`, compiled patterns              |
| 17 | `m_17_testing_pytest`       | asserts, fixtures, parametrize, `raises`, `tmp_path`, monkeypatch |
| 18 | `m_18_packaging_pyproject`  | src layout, `pyproject.toml`, entry points, `uv build`            |

Each lesson has a matching exercise `exercises/ex_NN_*.py` (stubs that raise
`NotImplementedError`), a reference implementation `solutions/ex_NN_*.py`, and tests in
`tests/test_ex_NN_*.py`.

## How to work

1. Run the lesson and read the code next to its output.
2. Open the exercise, read the docstrings (they include examples), implement the stubs.
3. Run the tests for that exercise until they pass.
4. Only then compare with the solution.

### Run a lesson

```bash
uv run python -m t02_intermediate.m_10_decorators
```

Lessons need no input or network and leave no files behind.

### Run the tests

```bash
uv run pytest t02_intermediate                    # all exercises (fail until you implement them)
uv run pytest t02_intermediate -k decorators      # one exercise by keyword
uv run pytest t02_intermediate -x                 # stop at the first failure
SOLUTIONS=1 uv run pytest t02_intermediate        # test the reference solutions instead
```

Before you start, failures are `NotImplementedError`. That is expected.

### Lint and format

```bash
uv run ruff check t02_intermediate && uv run ruff format t02_intermediate
```

## Progress checklist

- [ ] 01 Comprehensions: lesson read, exercise passing
- [ ] 02 `*args` / `**kwargs`: lesson read, exercise passing
- [ ] 03 lambda / map / filter / reduce: lesson read, exercise passing
- [ ] 04 Classes and objects: lesson read, exercise passing
- [ ] 05 Inheritance and composition: lesson read, exercise passing
- [ ] 06 Dunder methods: lesson read, exercise passing
- [ ] 07 Dataclasses: lesson read, exercise passing
- [ ] 08 Enums: lesson read, exercise passing
- [ ] 09 Iterators and generators: lesson read, exercise passing
- [ ] 10 Decorators: lesson read, exercise passing
- [ ] 11 Context managers: lesson read, exercise passing
- [ ] 12 Type hints: lesson read, exercise passing
- [ ] 13 pathlib / json / csv: lesson read, exercise passing
- [ ] 14 Logging: lesson read, exercise passing
- [ ] 15 Dates and times: lesson read, exercise passing
- [ ] 16 Regular expressions: lesson read, exercise passing
- [ ] 17 Testing with pytest: lesson read, exercise passing
- [ ] 18 Packaging with pyproject.toml: lesson read, exercise passing
- [ ] Mini-capstone below finished and tested
- [ ] `uv run ruff check t02_intermediate` is clean

## Mini-capstone: log-file analyzer CLI

Build `loganalyzer`, a small command line tool that summarizes an application log file.
Put it in its own folder (for example `capstone_t02/`) using a src layout.

Input: a text file with lines like
`2024-03-10 12:30:00 [ERROR] payments: card declined (user=42)`.

Requirements

1. **Parsing (regex + dataclasses)**: a frozen `LogEntry` dataclass (`timestamp` as an aware
   UTC `datetime`, `level` as a `StrEnum`, `component`, `message`, optional `user_id`).
   Parse with a compiled regex using named groups. Malformed lines are counted, not fatal.
2. **Streaming (generators)**: `read_entries(path)` is a generator; the whole file is never
   loaded into memory. Add generator stages such as `only_level(entries, level)` and
   `between(entries, start, end)`.
3. **Reporting**: totals per level, top 5 components by error count, first/last timestamp,
   busiest minute (use `collections.Counter`). Write the report as JSON with `pathlib` and
   optionally a CSV of the errors.
4. **CLI**: use `argparse` (`loganalyzer app.log --level ERROR --since 2024-03-10T00:00:00Z
   --json out.json`). Expose it via `[project.scripts]` in `pyproject.toml`.
5. **Logging**: the tool itself logs with `logging.getLogger(__name__)`; `-v` switches to
   DEBUG; configure handlers only in `main()`.
6. **Decorators / context managers**: a `@timed` decorator that logs how long parsing took,
   and a context manager that writes the output file atomically (temp file, then rename).
7. **Types**: full type hints, a `Protocol` for "something that yields entries", and a
   clean `pyright` or `mypy` run if you have it installed.
8. **Tests (pytest)**: parametrized parser tests, `tmp_path` fixtures for sample logs,
   `caplog` for the logging, `monkeypatch` for CLI arguments, and edge cases (empty file,
   bad lines, timezone offsets).

Stretch: add `--follow` using a generator that tails the file, and a `uv build` wheel you
can install with `uv tool install`.
