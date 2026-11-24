from datetime import date

import pytest

from _loader import load

ex = load("t08_forward_deployed", "ex_09_writing_runbooks_and_docs")

SPEC = ex.RunbookSpec(
    service="orders-sync",
    owner="Platform Team",
    overview="Syncs orders.",
    last_reviewed=date(2026, 11, 1),
    alerts=[
        ex.Alert(
            "SyncLagHigh",
            "Stale data.",
            ["Check dashboard.", "Check logs."],
            "Redeploy previous tag.",
        ),
        ex.Alert("DeadLetters", "Parked events.", ["List them."]),
    ],
    escalation=[ex.Contact("L1", "Team", "#oncall"), ex.Contact("L2", "FDE", "fde@x.example")],
)

EXPECTED_RUNBOOK = """# Runbook: orders-sync

Owner: Platform Team
Last reviewed: 2026-11-01

## Overview

Syncs orders.

## Alerts

### SyncLagHigh

**Meaning:** Stale data.

**First steps:**

1. Check dashboard.
2. Check logs.

**Rollback:** Redeploy previous tag.

### DeadLetters

**Meaning:** Parked events.

**First steps:**

1. List them.

## Escalation

| Role | Name | Channel |
|---|---|---|
| L1 | Team | #oncall |
| L2 | FDE | fde@x.example |
"""


def test_render_runbook_exact_output():
    assert ex.render_runbook(SPEC) == EXPECTED_RUNBOOK


def test_render_runbook_without_alerts_or_contacts():
    spec = ex.RunbookSpec("svc", "me", "Does things.", date(2026, 1, 2))
    assert ex.render_runbook(spec) == (
        "# Runbook: svc\n\nOwner: me\nLast reviewed: 2026-01-02\n\n## Overview\n\nDoes things.\n\n"
        "## Alerts\n\n_No alerts defined._\n\n## Escalation\n\n| Role | Name | Channel |\n|---|---|---|\n"
    )


def test_rendered_runbook_passes_lint():
    assert ex.lint_runbook(ex.render_runbook(SPEC)) == []


def test_render_adr_exact_output():
    adr = ex.ADR(
        7,
        "Use a queue",
        "accepted",
        "Webhooks time out.",
        "Queue between them.",
        ["Fast acks.", "One more component."],
    )
    assert ex.render_adr(adr) == (
        "# ADR-0007: Use a queue\n\nStatus: accepted\n\n## Context\n\nWebhooks time out.\n\n"
        "## Decision\n\nQueue between them.\n\n## Consequences\n\n- Fast acks.\n- One more component.\n"
    )


def test_render_adr_rejects_unknown_status():
    with pytest.raises(ValueError):
        ex.render_adr(ex.ADR(1, "t", "maybe", "c", "d", []))


def test_lint_reports_missing_sections_in_order():
    assert ex.lint_runbook("# Runbook\n## Overview\ntext") == [
        "missing section: ## Alerts",
        "missing section: ## Escalation",
    ]


def test_lint_flags_unfinished_text_whole_words_only():
    base = "## Overview\n## Alerts\n## Escalation\n"
    assert ex.lint_runbook(base + "TODO: fill in") == ["unfinished text"]
    assert ex.lint_runbook(base + "Use the TBD list") == ["unfinished text"]
    assert ex.lint_runbook(base + "The TODOLIST app and FIXMEs are fine") == []


@pytest.mark.parametrize(
    "leak",
    [
        "password = hunter2hunter2",
        "API_KEY: abcdef123456",
        "api-key=abcdef123456",
        "use sk_live_51Habcdef now",
        "key AKIAIOSFODNN7EXAMPLE here",
    ],
)
def test_lint_flags_secrets(leak):
    doc = "## Overview\n## Alerts\n## Escalation\n" + leak
    assert ex.lint_runbook(doc) == ["possible secret"]


def test_lint_allows_secret_placeholders():
    doc = "## Overview\n## Alerts\n## Escalation\ntoken: <from secrets manager>\npassword=$DB_PASSWORD\nsecret: [redacted]"
    assert ex.lint_runbook(doc) == []


def test_lint_combines_problems_in_order():
    assert ex.lint_runbook("TODO password = hunter2hunter2") == [
        "missing section: ## Overview",
        "missing section: ## Alerts",
        "missing section: ## Escalation",
        "unfinished text",
        "possible secret",
    ]


def test_stale_docs():
    today = date(2026, 11, 24)
    reviewed = {
        "zeta": date(2026, 1, 1),
        "alpha": date(2026, 5, 1),
        "fresh": date(2026, 11, 1),
        "boundary": date(2026, 8, 26),  # exactly 90 days ago: still fresh
        "just-over": date(2026, 8, 25),
    }
    assert ex.stale_docs(reviewed, today) == ["alpha", "just-over", "zeta"]
    assert ex.stale_docs(reviewed, today, max_age_days=10) == [
        "alpha",
        "boundary",
        "fresh",
        "just-over",
        "zeta",
    ]
