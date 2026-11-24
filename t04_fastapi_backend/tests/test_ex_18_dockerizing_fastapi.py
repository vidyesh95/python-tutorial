from pathlib import Path

from _loader import load

ex = load("t04_fastapi_backend", "ex_18_dockerizing_fastapi")

REAL_DOCKERFILE = Path(__file__).resolve().parents[1] / "docker" / "Dockerfile"

GOOD = """\
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
RUN pip install uv \\
    && uv --version

FROM python:3.13-slim
COPY --from=builder /app /app
USER app
HEALTHCHECK CMD true
"""


def test_parse_skips_comments_and_joins_continuations():
    assert ex.parse_dockerfile(GOOD) == [
        ("FROM", "python:3.13-slim AS builder"),
        ("RUN", "pip install uv && uv --version"),
        ("FROM", "python:3.13-slim"),
        ("COPY", "--from=builder /app /app"),
        ("USER", "app"),
        ("HEALTHCHECK", "CMD true"),
    ]


def test_parse_uppercases_instruction_and_ignores_blank_lines():
    assert ex.parse_dockerfile("\n\nfrom x:1\n\n  run   echo hi  \n") == [
        ("FROM", "x:1"),
        ("RUN", "echo hi"),
    ]


def test_stage_names():
    assert ex.stage_names(GOOD) == ["builder", "stage-1"]
    assert ex.stage_names("FROM a:1 as Base\nFROM Base AS final") == ["Base", "final"]
    assert ex.stage_names("RUN true") == []


def test_runs_as_non_root():
    assert ex.runs_as_non_root("FROM a:1\nUSER app") is True
    assert ex.runs_as_non_root("FROM a:1\nUSER 1001:1001") is True
    assert ex.runs_as_non_root("FROM a:1") is False
    assert ex.runs_as_non_root("FROM a:1\nUSER root") is False
    assert ex.runs_as_non_root("FROM a:1\nUSER app\nUSER 0") is False  # last one wins


def test_lint_clean_dockerfile():
    assert ex.lint_dockerfile(GOOD) == []


def test_lint_reports_problems_in_order():
    bad = "FROM python\nADD . /app\n"
    assert ex.lint_dockerfile(bad) == [
        "no USER instruction",
        "no HEALTHCHECK",
        "unpinned base image: python",
        "use COPY instead of ADD",
    ]


def test_lint_latest_root_and_scratch_and_stage_reference():
    text = "FROM node:latest AS web\nFROM scratch\nFROM web\nUSER root\nHEALTHCHECK CMD true\n"
    assert ex.lint_dockerfile(text) == ["runs as root", "unpinned base image: node:latest"]


def test_lint_registry_port_is_not_a_tag():
    assert ex.lint_dockerfile("FROM localhost:5000/app\nUSER x\nHEALTHCHECK CMD y") == [
        "unpinned base image: localhost:5000/app"
    ]


def test_repository_dockerfile_is_clean():
    text = REAL_DOCKERFILE.read_text()
    assert ex.lint_dockerfile(text) == []
    assert ex.stage_names(text) == ["builder", "runtime"]
    assert ex.runs_as_non_root(text)
