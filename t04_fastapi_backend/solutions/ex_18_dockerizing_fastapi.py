"""Exercise 18: Dockerizing FastAPI. Write a tiny Dockerfile linter (no Docker needed).

Tasks
1. parse_dockerfile: turn Dockerfile text into [(INSTRUCTION, args), ...].
2. stage_names: the name of every build stage.
3. runs_as_non_root: does the image end up running as a non-root user?
4. lint_dockerfile: list common problems. The repo's docker/Dockerfile must come back clean.

Run: uv run pytest t04_fastapi_backend -k dockerizing
"""

import re


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
    joined = re.sub(r"\s*\\\s*\n\s*", " ", text)
    pairs: list[tuple[str, str]] = []
    for raw in joined.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        instruction, _, args = line.partition(" ")
        pairs.append((instruction.upper(), args.strip()))
    return pairs


def stage_names(text: str) -> list[str]:
    """One entry per FROM. Use the `AS <name>` alias (case-insensitive 'as'); an unnamed stage
    is called "stage-<index>" where index is its 0-based position.

    >>> stage_names("FROM a AS builder\\nFROM b")
    ['builder', 'stage-1']
    """
    names: list[str] = []
    for instruction, args in parse_dockerfile(text):
        if instruction != "FROM":
            continue
        match = re.search(r"\s+as\s+(\S+)\s*$", args, re.IGNORECASE)
        names.append(match.group(1) if match else f"stage-{len(names)}")
    return names


def runs_as_non_root(text: str) -> bool:
    """True if the LAST `USER` instruction exists and is not "root" or "0".

    A `USER app:app` or `USER 1001` is non-root. No USER at all means root => False.
    """
    users = [args for instruction, args in parse_dockerfile(text) if instruction == "USER"]
    if not users:
        return False
    return users[-1].split(":")[0] not in {"root", "0"}


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
    pairs = parse_dockerfile(text)
    problems: list[str] = []

    if not any(instruction == "USER" for instruction, _ in pairs):
        problems.append("no USER instruction")
    elif not runs_as_non_root(text):
        problems.append("runs as root")

    if not any(instruction == "HEALTHCHECK" for instruction, _ in pairs):
        problems.append("no HEALTHCHECK")

    stages: set[str] = set()
    for instruction, args in pairs:
        if instruction != "FROM":
            continue
        parts = [p for p in args.split() if not p.startswith("--")]
        image = parts[0]
        known = image == "scratch" or image in stages or "@sha256:" in image
        if len(parts) >= 3 and parts[1].lower() == "as":
            stages.add(parts[2])
        if known:
            continue
        if ":" not in image.rsplit("/", 1)[-1] or image.endswith(":latest"):
            problems.append(f"unpinned base image: {image}")

    problems.extend("use COPY instead of ADD" for instruction, _ in pairs if instruction == "ADD")
    return problems
