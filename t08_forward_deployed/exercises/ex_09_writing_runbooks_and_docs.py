"""Exercise 09: generate runbook and ADR Markdown from data, lint docs, flag stale docs.

Tasks
1. render_runbook: RunbookSpec -> Markdown (exact format below).
2. render_adr: ADR -> Markdown (exact format below).
3. lint_runbook: required sections, unfinished text, accidentally pasted secrets.
4. stale_docs: which docs are overdue for review.

Run: uv run pytest t08_forward_deployed -k ex_09
"""

import re  # noqa: F401  (used by the solution)
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Alert:
    name: str
    meaning: str
    steps: list[str]
    rollback: str = ""


@dataclass
class Contact:
    role: str
    name: str
    channel: str


@dataclass
class RunbookSpec:
    service: str
    owner: str
    overview: str
    last_reviewed: date
    alerts: list[Alert] = field(default_factory=list)
    escalation: list[Contact] = field(default_factory=list)


@dataclass
class ADR:
    number: int
    title: str
    status: str  # proposed | accepted | deprecated | superseded
    context: str
    decision: str
    consequences: list[str]


def render_runbook(spec: RunbookSpec) -> str:
    """Return exactly this Markdown (blank lines matter; one trailing newline at the end):

        # Runbook: {service}

        Owner: {owner}
        Last reviewed: {last_reviewed as YYYY-MM-DD}

        ## Overview

        {overview}

        ## Alerts

        ### {alert.name}

        **Meaning:** {alert.meaning}

        **First steps:**

        1. {first step}
        2. {second step}

        **Rollback:** {alert.rollback}      <- this paragraph (and its blank line) ONLY if non-empty

        ### {next alert} ...                <- every alert block ends with ONE blank line

        ## Escalation

        | Role | Name | Channel |
        |---|---|---|
        | {role} | {name} | {channel} |

    With no alerts, the Alerts section contains the single line "_No alerts defined._" followed
    by a blank line. With no contacts only the two table header lines are printed.
    """
    raise NotImplementedError


def render_adr(adr: ADR) -> str:
    """Return exactly (one trailing newline; consequences are "- " bullets in order):

        # ADR-0007: {title}

        Status: {status}

        ## Context

        {context}

        ## Decision

        {decision}

        ## Consequences

        - {consequence 1}
        - {consequence 2}

    The number is zero-padded to 4 digits. A status outside proposed/accepted/deprecated/
    superseded raises ValueError.
    """
    raise NotImplementedError


def lint_runbook(markdown: str) -> list[str]:
    """Return a list of problems (empty list = clean), in this order:

    - for each of "## Overview", "## Alerts", "## Escalation" (in that order) not present:
      "missing section: ## Alerts" (using that heading)
    - "unfinished text" if the words TODO, FIXME or TBD appear (whole words, case-sensitive)
    - "possible secret" if ANY of these match:
        (?i)(password|secret|api[_-]?key|token)\\s*[:=]\\s*(?![<\\[$\\{])\\S{6,}   (placeholders that
            start with <, [, $ or { are fine, e.g. `token: <from secrets manager>`)
        \\bsk_(live|test)_\\w+
        AKIA[0-9A-Z]{16}
    """
    raise NotImplementedError


def stale_docs(reviewed: dict[str, date], today: date, max_age_days: int = 90) -> list[str]:
    """Names whose last review is MORE than `max_age_days` days before `today`, sorted
    alphabetically. A doc reviewed exactly `max_age_days` days ago is still fresh.
    """
    raise NotImplementedError
