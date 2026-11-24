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

import typer


def build_app() -> typer.Typer:
    """Create and return the Typer app described above."""
    raise NotImplementedError


def run_cli(app: typer.Typer, args: list[str]) -> tuple[int, str]:
    """Invoke `app` in-process with CliRunner; return (exit_code, stdout)."""
    raise NotImplementedError


def parse_kv(pairs: list[str]) -> dict[str, str]:
    """Parse "key=value" strings. Split on the first '=' only; ValueError if missing."""
    raise NotImplementedError
