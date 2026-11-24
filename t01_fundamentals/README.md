# Track 01 - Python Fundamentals

## Goals

By the end of this track you can:

- read and write idiomatic Python 3.13 (variables, types, operators, control flow);
- work with the core data structures: strings, lists, tuples, dicts and sets;
- write, document and test small functions, understand scope and closures;
- handle errors with exceptions, split code into modules, and read/write files;
- set up an isolated environment and manage dependencies with `venv`/`pip` and `uv`.

## Lessons

| File | Topic | What you learn |
| --- | --- | --- |
| `m_00_intro.py` | Intro | Running a Python file, the `__main__` guard |
| `m_01_variables.py` | Variables | Names, assignment, dynamic typing |
| `m_02_data_types.py` | Data types | int, float, complex, str, list, tuple, dict, set, bool, bytes, `type()` |
| `m_03_operators.py` | Operators | Arithmetic, comparison, logical, identity, membership, bitwise, precedence |
| `m_04_strings.py` | Strings | Indexing, slicing, methods, split/join, immutability |
| `m_05_numbers_math.py` | Numbers and math | Division flavours, rounding, float precision, `math`, `Decimal` |
| `m_06_input_output.py` | Input and output | `print`, `input`, f-strings, format specs |
| `m_07_conditionals.py` | Conditionals | `if/elif/else`, truthiness, ternary, `match/case` |
| `m_08_loops.py` | Loops | `for`, `while`, `break`, `continue`, `else`, `range`, `enumerate`, `zip` |
| `m_09_lists.py` | Lists | Mutation, sorting, slicing, copies, comprehensions |
| `m_10_tuples.py` | Tuples | Immutability, packing/unpacking, `namedtuple` |
| `m_11_dicts.py` | Dictionaries | Lookup, `get`, merging, comprehensions, counting/grouping |
| `m_12_sets.py` | Sets | Uniqueness, set algebra, `frozenset` |
| `m_13_functions.py` | Functions | Defaults, keyword args, `*args/**kwargs`, docstrings, recursion |
| `m_14_scope.py` | Scope and closures | LEGB, `global`, `nonlocal`, closures, late binding |
| `m_15_exceptions.py` | Exceptions | `try/except/else/finally`, `raise`, custom exceptions |
| `m_16_modules_imports.py` | Modules and imports | Import forms, `__main__` guard, `math`, `random`, `os`, `sys` |
| `m_17_file_io.py` | File I/O | `open`/`with`, modes, `pathlib`, JSON, CSV |
| `m_18_venv_uv_pip.py` | venv, pip and uv | Isolated environments, `uv init/add/run/sync`, `pyproject.toml` |

## Running a lesson

From the repository root:

```bash
uv run python -m t01_fundamentals.m_04_strings
```

Read the file top to bottom, run it, then change values and re-run to see what happens.

## Doing the exercises

Each lesson `NN` has a matching exercise in `exercises/ex_NN_<topic>.py`. Every function is a stub that raises
`NotImplementedError`; read the docstring (it has examples) and implement it. Tests live in `tests/`.

```bash
uv run pytest t01_fundamentals                   # everything (starts red)
uv run pytest t01_fundamentals -k strings        # one lesson
uv run pytest t01_fundamentals -k "lists or dicts"
SOLUTIONS=1 uv run pytest t01_fundamentals       # run the tests against the reference solutions
```

Try hard before peeking at `solutions/`. Failing with anything other than `NotImplementedError` means your code ran
but returned a wrong result - read the assertion diff.

## Checklist

- [ ] 00 Intro
- [ ] 01 Variables (lesson + exercise)
- [ ] 02 Data types
- [ ] 03 Operators
- [ ] 04 Strings
- [ ] 05 Numbers and math
- [ ] 06 Input and output
- [ ] 07 Conditionals
- [ ] 08 Loops
- [ ] 09 Lists
- [ ] 10 Tuples
- [ ] 11 Dictionaries
- [ ] 12 Sets
- [ ] 13 Functions
- [ ] 14 Scope and closures
- [ ] 15 Exceptions
- [ ] 16 Modules and imports
- [ ] 17 File I/O
- [ ] 18 venv, pip and uv
- [ ] Capstone finished

## Mini-capstone: command-line expense (or todo) tracker

Build a small CLI using only the standard library. Suggested scope:

- Commands: `add "coffee" 3.50`, `list`, `total`, `delete <id>` (swap in `todo add/done/list` if you prefer).
- Parse arguments with `sys.argv` first, then upgrade to `argparse`.
- Store entries as a list of dicts and persist them to a JSON file (`json`, `pathlib`).
- Validate input and report friendly errors with custom exceptions.
- Format output as an aligned table with f-strings.
- Put logic in functions, keep the CLI in a `main()` guarded by `if __name__ == "__main__"`.
- Stretch goals: filter by date (`datetime`), group totals by category (`dict`), write tests with `pytest` and
  `tmp_path`, and manage the project with `uv init`.
