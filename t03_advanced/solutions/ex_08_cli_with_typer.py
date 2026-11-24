"""Exercise 08: Command-Line Apps with Typer.

Tasks
1. build_app() returns a Typer app (a fresh one on every call) with these commands:
   - `add A B`: two int arguments; prints their sum.
   - `greet NAME [--greeting TEXT] [--shout]`: prints "<greeting>, <NAME>!" (default
     greeting "Hello"); with --shout the whole line is uppercased.
   - `divide A B`: two floats; prints A / B. If B is 0, write "division by zero" to stderr
     and exit with code 1.
   - `tags add TAG` and `tags list`: a sub-command group. `tags add` prints "added <TAG>";
     `tags list` prints the tags added so far (this app instance), one per line, or
     "(none)". State must be per app instance (use a closure, not a module global).
2. run_cli(app, args) invokes the app with typer.testing.CliRunner and returns
   (exit_code, stdout).
3. parse_kv(pairs) turns ["a=1", "b=2"] into {"a": "1", "b": "2"}; raise ValueError on an
   item without "=". Splits on the first "=" only.

Run: uv run pytest t03_advanced -k typer
"""

from typing import Annotated

import typer
from typer.testing import CliRunner


def build_app() -> typer.Typer:
    """Create and return the Typer app described above."""
    app = typer.Typer()
    tags_app = typer.Typer()
    app.add_typer(tags_app, name="tags")
    tags: list[str] = []

    @app.command()
    def add(a: int, b: int) -> None:
        typer.echo(a + b)

    @app.command()
    def greet(
        name: str,
        greeting: Annotated[str, typer.Option("--greeting")] = "Hello",
        shout: Annotated[bool, typer.Option("--shout")] = False,
    ) -> None:
        line = f"{greeting}, {name}!"
        typer.echo(line.upper() if shout else line)

    @app.command()
    def divide(a: float, b: float) -> None:
        if b == 0:
            typer.echo("division by zero", err=True)
            raise typer.Exit(code=1)
        typer.echo(a / b)

    @tags_app.command("add")
    def tags_add(tag: str) -> None:
        tags.append(tag)
        typer.echo(f"added {tag}")

    @tags_app.command("list")
    def tags_list() -> None:
        typer.echo("\n".join(tags) if tags else "(none)")

    return app


def run_cli(app: typer.Typer, args: list[str]) -> tuple[int, str]:
    """Invoke `app` in-process with CliRunner; return (exit_code, stdout)."""
    result = CliRunner().invoke(app, args)
    return result.exit_code, result.stdout


def parse_kv(pairs: list[str]) -> dict[str, str]:
    """Parse "key=value" strings. Split on the first '=' only; ValueError if missing."""
    out: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise ValueError(f"expected key=value, got {pair!r}")
        out[key] = value
    return out
