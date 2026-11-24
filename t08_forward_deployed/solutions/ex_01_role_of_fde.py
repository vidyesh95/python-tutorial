"""Reference solution for exercise 01."""

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
    for value in (likelihood, impact):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"score inputs must be ints in 1..5, got {value!r}")
    return likelihood * impact


def risk_level(score: int) -> str:
    return "HIGH" if score >= 15 else "MEDIUM" if score >= 8 else "LOW"


def top_risks(risks: list[Risk], n: int = 3) -> list[Risk]:
    if n <= 0:
        return []
    ranked = sorted(risks, key=lambda r: (-(r.likelihood * r.impact), r.name))
    return ranked[:n]


def open_topics(answers: dict[str, str | None]) -> list[str]:
    return sorted(topic for topic, answer in answers.items() if not (answer or "").strip())


def next_phase(current: Phase, satisfied: set[str]) -> Phase:
    order = list(Phase)
    index = order.index(current)
    if index == len(order) - 1 or not EXIT_GATES[current] <= satisfied:
        return current
    return order[index + 1]


def format_status_update(done: str, impact: str, next_step: str, eta: str) -> str:
    fields = {"Done": done, "Impact": impact, "Next": next_step, "ETA": eta}
    cleaned = {label: value.strip() for label, value in fields.items()}
    for label, value in cleaned.items():
        if not value:
            raise ValueError(f"{label} must not be empty")
    return "\n".join(f"{label}: {value}" for label, value in cleaned.items())
