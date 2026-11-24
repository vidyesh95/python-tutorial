from pathlib import Path

from _loader import load

ex = load("t05_cloud_engineering", "ex_11_ci_cd_github_actions")

SAMPLE = """\
# a comment: not a key
name: demo
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: some/tool@main
      - run: uv sync
      - name: multi
        run: |
          uv run ruff check .

          SOLUTIONS=1 uv run pytest
      - name: after block
        run: echo done
  release-it:
    needs: build
    steps:
      - uses: ./local-action
      - uses: docker://alpine:3
      - uses: bare/action
      - uses: other/thing@latest
env:
  X: 1
"""

CI_YML = Path(__file__).resolve().parents[1] / "ci" / "ci.yml"


def test_top_level_keys():
    assert ex.top_level_keys(SAMPLE) == ["name", "on", "jobs", "env"]


def test_job_names_stop_at_next_top_level_key():
    assert ex.job_names(SAMPLE) == ["build", "release-it"]


def test_uses_actions_in_order():
    assert ex.uses_actions(SAMPLE) == [
        "actions/checkout@v4",
        "some/tool@main",
        "./local-action",
        "docker://alpine:3",
        "bare/action",
        "other/thing@latest",
    ]


def test_run_commands_single_and_block():
    assert ex.run_commands(SAMPLE) == [
        "uv sync",
        "uv run ruff check .",
        "SOLUTIONS=1 uv run pytest",
        "echo done",
    ]


def test_find_unpinned_actions():
    assert ex.find_unpinned_actions(SAMPLE) == [
        "some/tool@main",
        "bare/action",
        "other/thing@latest",
    ]


def test_real_ci_workflow():
    text = CI_YML.read_text()
    assert ex.top_level_keys(text) == ["name", "on", "permissions", "concurrency", "jobs"]
    assert ex.job_names(text) == ["test", "deploy"]
    commands = ex.run_commands(text)
    assert "uv sync --all-groups" in commands
    assert "uv run ruff check ." in commands
    assert "SOLUTIONS=1 uv run pytest" in commands
    assert ex.find_unpinned_actions(text) == []
    assert "astral-sh/setup-uv@v6" in ex.uses_actions(text)
