"""Exercise 18: Dockerizing FastAPI. Write a tiny Dockerfile linter (no Docker needed).

Tasks
1. parse_dockerfile: turn Dockerfile text into [(INSTRUCTION, args), ...].
2. stage_names: the name of every build stage.
3. runs_as_non_root: does the image end up running as a non-root user?
4. lint_dockerfile: list common problems. The repo's docker/Dockerfile must come back clean.

Run: uv run pytest t04_fastapi_backend -k dockerizing
"""


def parse_dockerfile(text: str) -> list[tuple[str, str]]:
    """Return (INSTRUCTION, args) pairs in order.

    - Blank lines and lines starting with '#' are skipped (this also drops the
      `# syntax=` directive).
    - A trailing backslash joins a line with the next one (replace it with a single
      space; collapse the join so args have no double spaces at the seam).
    - INSTRUCTION is upper-cased; args are stripped.

    A file with `from python:3.13-slim as b`, then `RUN a \\` and `  && b` on the next
    line gives [('FROM', 'python:3.13-slim as b'), ('RUN', 'a && b')].
    """
    raise NotImplementedError


def stage_names(text: str) -> list[str]:
    """One entry per FROM. Use the `AS <name>` alias (case-insensitive 'as'); an unnamed stage
    is called "stage-<index>" where index is its 0-based position.

    >>> stage_names("FROM a AS builder\\nFROM b")
    ['builder', 'stage-1']
    """
    raise NotImplementedError


def runs_as_non_root(text: str) -> bool:
    """True if the LAST `USER` instruction exists and is not "root" or "0".

    A `USER app:app` or `USER 1001` is non-root. No USER at all means root => False.
    """
    raise NotImplementedError


def lint_dockerfile(text: str) -> list[str]:
    """Return a list of problem messages (empty if clean). Check, in this order:

    1. "no USER instruction" / "runs as root" (use runs_as_non_root)
    2. "no HEALTHCHECK"
    3. For each FROM whose image has no tag or uses ':latest' (ignore `FROM scratch` and
       stage references): f"unpinned base image: {image}"
    4. For each ADD instruction: "use COPY instead of ADD"

    Messages are exactly the quoted strings above (1: pick 'no USER instruction' when there
    is none, 'runs as root' when the last USER is root/0).
    """
    raise NotImplementedError
