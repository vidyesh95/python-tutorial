"""Exercise 11: analyse a GitHub Actions workflow given as TEXT (no YAML library needed).

The tests use small inline workflows plus the real `ci/ci.yml` of this track. Assume the
conventional formatting: top-level keys at column 0, job names indented by exactly 2 spaces.

Tasks
1. top_level_keys: the unindented keys (name, on, permissions, jobs...).
2. job_names: the job ids under `jobs:`.
3. uses_actions: every `uses:` value in file order.
4. run_commands: the shell commands from `run:` steps (single line or `run: |` blocks).
5. find_unpinned_actions: actions without a pinned version.

Run: uv run pytest t05_cloud_engineering -k github_actions
"""

import re


def top_level_keys(text: str) -> list[str]:
    """Return keys that start at column 0 and look like `key:` (letters, digits, '_', '-';
    must not start with a digit), in order. Ignore comment lines and indented lines.
    """
    return [
        m.group(1) for line in text.splitlines() if (m := re.match(r"^([A-Za-z_][\w-]*):", line))
    ]


def job_names(text: str) -> list[str]:
    """Return job ids: lines indented by exactly two spaces of the form `  name:` that
    appear inside the top-level `jobs:` block (stop at the next top-level key).
    """
    names, in_jobs = [], False
    for line in text.splitlines():
        if re.match(r"^[A-Za-z_]", line):
            in_jobs = line.startswith("jobs:")
        elif in_jobs and (m := re.match(r"^  ([\w-]+):\s*$", line)):
            names.append(m.group(1))
    return names


def uses_actions(text: str) -> list[str]:
    """Return the value of every `uses:` key (also when written as `- uses: x@v1`), in file
    order. Values contain no spaces.
    """
    return re.findall(r"^\s*-?\s*uses:\s*(\S+)", text, flags=re.MULTILINE)


def run_commands(text: str) -> list[str]:
    """Return the commands of `run:` steps, in file order.

    - `run: uv sync` -> "uv sync" (works for `- run: ...` too)
    - `run: |` (or `>`, `|-`, `>-`) followed by more-indented lines -> each non-empty line
      of the block, stripped, as its own entry.
    """
    commands: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", lines[i])
        i += 1
        if not m:
            continue
        indent, rest = len(m.group(1)), m.group(2).strip()
        if rest in ("|", ">", "|-", ">-"):
            while i < len(lines):
                line = lines[i]
                if line.strip() and len(line) - len(line.lstrip()) <= indent:
                    break
                if line.strip():
                    commands.append(line.strip())
                i += 1
        elif rest:
            commands.append(rest)
    return commands


def find_unpinned_actions(text: str) -> list[str]:
    """Return `uses:` values that are risky: no "@version" at all, or version one of
    "main", "master", "latest", "HEAD". Ignore local actions (start with "./") and
    docker:// references. Keep file order.
    """
    risky = []
    for ref in uses_actions(text):
        if ref.startswith(("./", "docker://")):
            continue
        _, _, version = ref.partition("@")
        if version in ("", "main", "master", "latest", "HEAD"):
            risky.append(ref)
    return risky
