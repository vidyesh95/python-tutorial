"""Exercise 01: engagement planning helpers (risk scoring, gates, status updates).

Tasks
1. risk_score / risk_level: likelihood x impact on a 1..5 scale, with validation.
2. top_risks: the n highest-scoring risks, deterministic order.
3. open_topics: which discovery topics still have no answer.
4. next_phase: advance a phase only when every exit-gate item is satisfied.
5. format_status_update: the fixed-shape weekly update.

Run: uv run pytest t08_forward_deployed -k ex_01
"""

from dataclasses import dataclass
from enum import StrEnum


class Phase(StrEnum):
    DISCOVERY = "discovery"
    SCOPING = "scoping"
    PROTOTYPE = "prototype"
    PRODUCTION = "production"
    HANDOFF = "handoff"


EXIT_GATES: dict[Phase, set[str]] = {
    Phase.DISCOVERY: {"goal agreed", "data sources listed"},
    Phase.SCOPING: {"scope signed off", "risks reviewed"},
    Phase.PROTOTYPE: {"demo done"},
    Phase.PRODUCTION: {"security review passed", "monitoring live"},
    Phase.HANDOFF: {"customer ran it unaided"},
}


@dataclass
class Risk:
    name: str
    likelihood: int
    impact: int


def risk_score(likelihood: int, impact: int) -> int:
    """Return likelihood * impact. Both must be ints in 1..5; otherwise raise ValueError."""
    raise NotImplementedError


def risk_level(score: int) -> str:
    """ "HIGH" for score >= 15, "MEDIUM" for score >= 8, otherwise "LOW"."""
    raise NotImplementedError


def top_risks(risks: list[Risk], n: int = 3) -> list[Risk]:
    """The n risks with the highest score. Ties are broken alphabetically by name.
    Do not mutate the input list. n <= 0 returns [].
    """
    raise NotImplementedError


def open_topics(answers: dict[str, str | None]) -> list[str]:
    """Topics whose answer is None, empty or only whitespace, sorted alphabetically."""
    raise NotImplementedError


def next_phase(current: Phase, satisfied: set[str]) -> Phase:
    """Return the following Phase (in enum order) if EXIT_GATES[current] is a subset of
    `satisfied`; otherwise return `current`. HANDOFF has no next phase: always return HANDOFF.
    """
    raise NotImplementedError


def format_status_update(done: str, impact: str, next_step: str, eta: str) -> str:
    """Four lines, in this order, no trailing newline:
    "Done: ...", "Impact: ...", "Next: ...", "ETA: ...".
    Each value is stripped. Raise ValueError if any value is empty after stripping.
    """
    raise NotImplementedError
