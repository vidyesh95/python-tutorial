# Writing Runbooks and Docs
"""
The integration is only done when the customer can run it without you. Documentation is the
product of the handoff: a stranger on call at 3am should fix the most likely problems using
only what you wrote.

THREE DOCUMENTS THAT MATTER
1. RUNBOOK (operational, read during an incident): what the service does, how to see its health,
   and for each alert: what it MEANS, how to CONFIRM, the FIRST steps, how to ROLL BACK, and who
   to ESCALATE to. Numbered, imperative, copy-pasteable commands. No prose essays.
2. ADR, Architecture Decision Record (why, read months later): one short file per decision with
   Context, Decision, Consequences, Status (proposed / accepted / superseded by ADR-N). It stops
   the "why on earth did we do it this way?" debates and survives staff changes.
3. HANDOFF DOC (transition, read once, then referenced): architecture and data-flow overview, where
   things live (repos, dashboards, secrets paths), owners, known issues, access to revoke or
   transfer, support contacts, and a "first week" checklist for the new owner.

WRITING RULES
- Write for the reader under stress: put the answer first, one action per step, say what a good
  result looks like ("expect HTTP 200 and `status: ok`").
- Every alert in monitoring links to a runbook section with the SAME name.
- Never put secrets in docs: write WHERE they live (`secrets manager path`) and who can grant
  access. Docs get emailed, copied, and indexed.
- Keep docs next to the code (Markdown in the repo, reviewed in pull requests) and add a
  `Last reviewed` date; stale docs are worse than none because people trust them.
- Test the runbook: have someone who did not build the system follow it (a "game day").

CODE: generate Markdown from structured data (dataclasses), so every runbook has the same shape
and a linter can check it (required sections, TODOs left behind, accidentally pasted secrets,
stale review dates). Run: uv run python -m t08_forward_deployed.m_09_writing_runbooks_and_docs
"""

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
    dashboards: dict[str, str] = field(default_factory=dict)  # label -> URL
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


# Example 1: structured data -> consistent Markdown
def render_runbook(spec: RunbookSpec) -> str:
    out = [
        f"# Runbook: {spec.service}",
        "",
        f"Owner: {spec.owner}  ",
        f"Last reviewed: {spec.last_reviewed.isoformat()}",
        "",
        "## Overview",
        "",
        spec.overview,
        "",
    ]
    if spec.dashboards:
        out += (
            ["## Dashboards", ""]
            + [f"- [{label}]({url})" for label, url in spec.dashboards.items()]
            + [""]
        )
    out += ["## Alerts", ""]
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


def render_adr(adr: ADR) -> str:
    consequences = "\n".join(f"- {c}" for c in adr.consequences)
    return (
        f"# ADR-{adr.number:04d}: {adr.title}\n\n"
        f"Status: {adr.status}\n\n## Context\n\n{adr.context}\n\n"
        f"## Decision\n\n{adr.decision}\n\n## Consequences\n\n{consequences}\n"
    )


def render_handoff(
    customer: str, owners: dict[str, str], locations: dict[str, str], known_issues: list[str]
) -> str:
    lines = [f"# Handoff: {customer} integration", "", "## Owners", ""]
    lines += [f"- **{area}:** {who}" for area, who in owners.items()]
    lines += ["", "## Where things live (no secrets here, only locations)", ""]
    lines += [f"- {what}: `{where}`" for what, where in locations.items()]
    lines += ["", "## Known issues", ""] + [f"- {issue}" for issue in known_issues]
    lines += [
        "",
        "## First-week checklist for the new owner",
        "",
        "- [ ] You can open the dashboards and see data",
        "- [ ] You received (and tested) the on-call alert route",
        "- [ ] You rotated one secret following the runbook",
        "",
    ]
    return "\n".join(lines)


# Example 2: lint the docs like code
REQUIRED_SECTIONS = ["## Overview", "## Alerts", "## Escalation"]
SECRET_PATTERNS = [
    re.compile(r"(?i)(password|secret|api[_-]?key|token)\s*[:=]\s*\S{6,}"),
    re.compile(r"\bsk_(live|test)_\w+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def lint_runbook(markdown: str) -> list[str]:
    problems = [f"missing section: {s}" for s in REQUIRED_SECTIONS if s not in markdown]
    if re.search(r"\b(TODO|FIXME|TBD)\b", markdown):
        problems.append("unfinished text (TODO/FIXME/TBD)")
    if any(p.search(markdown) for p in SECRET_PATTERNS):
        problems.append("possible secret in document")
    return problems


def stale_docs(reviewed: dict[str, date], today: date, max_age_days: int = 90) -> list[str]:
    return sorted(name for name, when in reviewed.items() if (today - when).days > max_age_days)


def sample_spec() -> RunbookSpec:
    return RunbookSpec(
        service="orders-sync",
        owner="Acme Platform Team (platform@acme.example)",
        overview="Pulls orders from the ERP every 5 minutes, normalizes them and loads the warehouse.",
        last_reviewed=date(2026, 11, 1),
        dashboards={"Sync health": "https://grafana.acme.example/d/orders-sync"},
        alerts=[
            Alert(
                "SyncLagHigh",
                "No successful sync for 15 minutes; downstream reports are stale.",
                [
                    "Open the Sync health dashboard and check the `last_success_age` panel.",
                    "Search logs for the latest `correlation_id` with `level=ERROR`.",
                    "If the ERP returns HTTP 429/5xx, wait: the client retries with backoff.",
                    "If HTTP 401, rotate the credential (see 'Rotate the ERP key') and re-run.",
                ],
                rollback="Re-deploy the previous image tag from the release page.",
            ),
            Alert(
                "DeadLetterNotEmpty",
                "Events failed 3 times and were parked.",
                [
                    "List dead letters: `orders-sync dlq list`.",
                    "Fix the cause, then `orders-sync dlq replay`.",
                ],
            ),
        ],
        escalation=[
            Contact("L1 on-call", "Acme platform rotation", "#acme-platform-oncall"),
            Contact("L2 engineer", "FDE (until handoff ends)", "fde@vendor.example"),
        ],
    )


def run_demo() -> None:
    runbook = render_runbook(sample_spec())
    print(runbook)
    print("lint problems:", lint_runbook(runbook))
    print(
        "lint on a bad doc:",
        lint_runbook("# Runbook\n## Overview\nTODO\npassword = hunter2hunter2"),
    )
    print(
        render_adr(
            ADR(
                7,
                "Use a queue between the webhook receiver and the worker",
                "accepted",
                "The ERP times out webhooks after 5s, but loading takes up to 30s.",
                "The receiver verifies, stores the event in SQS and returns 202; a worker processes it.",
                [
                    "Webhooks are acknowledged fast and retried safely.",
                    "We operate one more component (queue + DLQ).",
                ],
            )
        )
    )
    handoff = render_handoff(
        "Acme Logistics",
        {"Service owner": "Acme Platform Team", "Escalation": "FDE until 2026-12-15"},
        {
            "Repository": "github.com/acme/orders-sync",
            "ERP API key": "secrets manager: acme/orders-sync/erp-key",
        },
        ["Sandbox ERP rate limit is lower than production (60 vs 600 req/min)."],
    )
    print(handoff)
    print(
        "stale docs:",
        stale_docs({"runbook": date(2026, 11, 1), "handoff": date(2026, 5, 1)}, date(2026, 11, 24)),
    )


"""
Common mistakes:
- Writing the runbook after the incident, from memory, by the one person who knows the system.
- Explaining architecture instead of giving steps; or steps that need tribal knowledge.
- Commands that only work on your laptop (hardcoded paths, personal credentials, missing context).
- Screenshots of dashboards instead of links; links that require access nobody has.
- No owner and no review date, so the doc silently rots.
- Pasting a real token "so the example works". Use placeholders and point to the secret manager.
- A handoff that is a meeting, not a document (the knowledge leaves with the attendees).

In the field:
- Start the runbook in week 1 and update it every time something breaks: the incident timeline
  (m_08) is its best source material.
- Do a handoff rehearsal: the customer's engineer restarts the service and handles a fake alert
  while you only watch.
- Link alert -> runbook section -> dashboard, and keep one escalation table in a known place.
- Record decisions as ADRs the day you make them; four sentences are enough.
"""

if __name__ == "__main__":
    run_demo()
