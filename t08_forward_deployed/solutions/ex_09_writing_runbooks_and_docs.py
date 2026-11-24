"""Reference solution for exercise 09."""

import re
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
    status: str
    context: str
    decision: str
    consequences: list[str]


def render_runbook(spec: RunbookSpec) -> str:
    out = [
        f"# Runbook: {spec.service}",
        "",
        f"Owner: {spec.owner}",
        f"Last reviewed: {spec.last_reviewed.isoformat()}",
        "",
        "## Overview",
        "",
        spec.overview,
        "",
        "## Alerts",
        "",
    ]
    if not spec.alerts:
        out += ["_No alerts defined._", ""]
    for alert in spec.alerts:
        out += [
            f"### {alert.name}",
            "",
            f"**Meaning:** {alert.meaning}",
            "",
            "**First steps:**",
            "",
        ]
        out += [f"{i}. {step}" for i, step in enumerate(alert.steps, start=1)]
        if alert.rollback:
            out += ["", f"**Rollback:** {alert.rollback}"]
        out.append("")
    out += ["## Escalation", "", "| Role | Name | Channel |", "|---|---|---|"]
    out += [f"| {c.role} | {c.name} | {c.channel} |" for c in spec.escalation]
    return "\n".join(out) + "\n"


_STATUSES = {"proposed", "accepted", "deprecated", "superseded"}


def render_adr(adr: ADR) -> str:
    if adr.status not in _STATUSES:
        raise ValueError(f"invalid ADR status: {adr.status!r}")
    bullets = "\n".join(f"- {c}" for c in adr.consequences)
    return (
        f"# ADR-{adr.number:04d}: {adr.title}\n\n"
        f"Status: {adr.status}\n\n"
        f"## Context\n\n{adr.context}\n\n"
        f"## Decision\n\n{adr.decision}\n\n"
        f"## Consequences\n\n{bullets}\n"
    )


_SECRETS = [
    re.compile(r"(?i)(password|secret|api[_-]?key|token)\s*[:=]\s*(?![<\[$\{])\S{6,}"),
    re.compile(r"\bsk_(live|test)_\w+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def lint_runbook(markdown: str) -> list[str]:
    problems = [
        f"missing section: {heading}"
        for heading in ("## Overview", "## Alerts", "## Escalation")
        if heading not in markdown
    ]
    if re.search(r"\b(TODO|FIXME|TBD)\b", markdown):
        problems.append("unfinished text")
    if any(pattern.search(markdown) for pattern in _SECRETS):
        problems.append("possible secret")
    return problems


def stale_docs(reviewed: dict[str, date], today: date, max_age_days: int = 90) -> list[str]:
    return sorted(name for name, when in reviewed.items() if (today - when).days > max_age_days)
