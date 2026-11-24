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

import re  # noqa: F401  (handy for all tasks)


def top_level_keys(text: str) -> list[str]:
    """Return keys that start at column 0 and look like `key:` (letters, digits, '_', '-';
    must not start with a digit), in order. Ignore comment lines and indented lines.
    """
    raise NotImplementedError


def job_names(text: str) -> list[str]:
    """Return job ids: lines indented by exactly two spaces of the form `  name:` that
    appear inside the top-level `jobs:` block (stop at the next top-level key).
    """
    raise NotImplementedError


def uses_actions(text: str) -> list[str]:
    """Return the value of every `uses:` key (also when written as `- uses: x@v1`), in file
    order. Values contain no spaces.
    """
    raise NotImplementedError


def run_commands(text: str) -> list[str]:
    """Return the commands of `run:` steps, in file order.

    - `run: uv sync` -> "uv sync" (works for `- run: ...` too)
    - `run: |` (or `>`, `|-`, `>-`) followed by more-indented lines -> each non-empty line
      of the block, stripped, as its own entry.
    """
    raise NotImplementedError


def find_unpinned_actions(text: str) -> list[str]:
    """Return `uses:` values that are risky: no "@version" at all, or version one of
    "main", "master", "latest", "HEAD". Ignore local actions (start with "./") and
    docker:// references. Keep file order.
    """
    raise NotImplementedError
