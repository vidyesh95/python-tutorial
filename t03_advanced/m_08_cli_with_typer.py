# Command-Line Apps with Typer
"""
Typer builds a CLI from ordinary type-annotated functions (it sits on top of Click and, like
FastAPI, is made by the same author). The type hints become argument parsing, validation,
`--help` text, and shell completion.

Core ideas:
- `app = typer.Typer()` holds commands. `@app.command()` registers a function.
- A parameter WITHOUT a default is a required ARGUMENT; WITH a default it is an OPTION
  (`--name`). Use `Annotated[T, typer.Option(...)]` / `typer.Argument(...)` for details.
- bool options become flags (`--verbose / --no-verbose`). Enums become choices.
- Several `@app.command()` functions give subcommands: `tool add`, `tool list`.
- Exit codes: `raise typer.Exit(code=2)`; errors for the user: print to stderr and Exit.
- Test with `typer.testing.CliRunner`: invoke the app in-process, check `.exit_code` and
  `.output`. No subprocesses, no shell.
- `app()` is what you call from `if __name__ == "__main__"` or a `[project.scripts]`
  entry point. Here we only call it through CliRunner so the lesson stays non-interactive.

Common mistakes:
- Calling `app()` at import time (it parses sys.argv and exits). Guard it with __main__.
- Putting business logic inside the command body. Keep it in plain functions, call them from
  the command, and unit-test those directly.
- Using print for errors. Use `typer.echo(..., err=True)` and a non-zero exit code.
- Mutable global state shared between commands. Use `typer.Context` / callbacks instead.

Where this shows up in backend/ML/robotics work:
- Backend: admin/maintenance commands (migrate, seed, reindex), ops scripts, worker launchers.
- ML: `train`, `evaluate`, `export` commands driven by config flags.
- Robotics: calibration, log replay and fleet tooling run over SSH on headless machines.
"""

from enum import StrEnum
from typing import Annotated

import typer
from typer.testing import CliRunner


# Business logic lives in plain functions (easy to test without the CLI)
def make_greeting(name: str, shout: bool = False, times: int = 1) -> list[str]:
    line = f"Hello, {name}!"
    return [line.upper() if shout else line] * times


class Level(StrEnum):
    low = "low"
    high = "high"


app = typer.Typer(help="Demo tool with a few commands.", no_args_is_help=True)


# Example: a command: `name` is an argument, `--shout` a flag, `--times` an option
@app.command()
def greet(
    name: Annotated[str, typer.Argument(help="Who to greet.")],
    shout: Annotated[bool, typer.Option("--shout", "-s", help="Uppercase the greeting.")] = False,
    times: Annotated[int, typer.Option(min=1, max=5, help="Repeat count.")] = 1,
) -> None:
    """Greet NAME politely."""
    for line in make_greeting(name, shout, times):
        typer.echo(line)


# Example: enums become validated choices; typer.Exit sets the exit code
@app.command()
def check(
    value: int,
    level: Level = Level.low,
) -> None:
    """Pretend to validate VALUE against a threshold LEVEL."""
    limit = {Level.low: 10, Level.high: 100}[level]
    if value > limit:
        typer.echo(f"{value} exceeds {limit}", err=True)  # stderr, not stdout
        raise typer.Exit(code=3)
    typer.echo(f"{value} ok for {level.value}")


# Example: subcommand groups: a nested Typer app added with add_typer
items_app = typer.Typer(help="Manage an in-memory item list.")
app.add_typer(items_app, name="items")
STORE: list[str] = []


@items_app.command("add")
def items_add(item: str) -> None:
    STORE.append(item)
    typer.echo(f"added {item!r}; total={len(STORE)}")


@items_app.command("list")
def items_list() -> None:
    typer.echo(", ".join(STORE) or "(empty)")


# Example: demo through CliRunner (what your pytest tests would do)
runner = CliRunner()

result = runner.invoke(app, ["greet", "Ada"])
print("exit", result.exit_code, "->", result.output.strip())

result = runner.invoke(app, ["greet", "Ada", "--shout", "--times", "2"])
print("exit", result.exit_code, "->", result.output.split())

result = runner.invoke(app, ["greet", "Ada", "--times", "9"])  # violates max=5
print("bad option exit:", result.exit_code)  # 2 = usage error, handled by Click

result = runner.invoke(app, ["check", "50", "--level", "high"])
print("check:", result.exit_code, result.output.strip())

result = runner.invoke(app, ["check", "50"])  # default low limit 10
print("check:", result.exit_code)  # 3, from typer.Exit(code=3)

result = runner.invoke(app, ["check", "5", "--level", "medium"])  # not in the enum
print("bad choice exit:", result.exit_code)

runner.invoke(app, ["items", "add", "apple"])
result = runner.invoke(app, ["items", "add", "pear"])
print(result.output.strip())
print("list:", runner.invoke(app, ["items", "list"]).output.strip())

result = runner.invoke(app, ["--help"])
print("help mentions commands:", all(c in result.output for c in ("greet", "check", "items")))
print("greet help:", "Greet NAME politely." in runner.invoke(app, ["greet", "--help"]).output)

# Stretch: real entry point (not run here, because it would parse sys.argv):
#     if __name__ == "__main__":
#         app()
# and in pyproject.toml:  [project.scripts]  mytool = "package.cli:app"
