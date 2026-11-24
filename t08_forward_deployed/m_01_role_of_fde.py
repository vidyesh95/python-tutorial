# The Forward-Deployed Engineer Role
"""
A Forward-Deployed Engineer (FDE) is a software engineer embedded with a customer. You own an
outcome ("their invoices flow into our product within 6 weeks") rather than a component. You
write production code, but most of the value comes from choosing the right thing to build and
making the customer's team able to run it without you.

How the role differs
- Product engineer: builds a general feature for many customers, far from any one of them.
- Solutions / sales engineer: demos and designs, usually does not ship production code.
- FDE: ships working integrations inside one customer's constraints (their data, auth,
  network, security review), then feeds what you learn back to the product team.

The engagement lifecycle (every phase has an exit gate, you do not drift between them)
1. DISCOVERY   interviews + reading their systems: goals, data sources, owners, constraints.
2. SCOPING     turn goals into a written scope, success metrics and a risk register.
3. PROTOTYPE   the thinnest end-to-end slice on sample/sandbox data, demoed within days.
4. PRODUCTION  harden: auth, retries, monitoring, tests, security review, real data.
5. HANDOFF     runbook, docs, training, a named customer owner. You are now optional.

Customer communication habits
- Weekly written status in the same shape: what happened, impact, next step, date.
- Bad news early, with options: "X will slip 3 days; we can cut Y or add a second reviewer."
- Write down every decision and who made it. Confirm scope changes in writing.
- Say "I do not know yet, I will know by Thursday" instead of guessing.

Security posture (non-negotiable, and the fastest way to build trust)
- Customer data stays in the customer's environment unless a written agreement says otherwise.
- Least privilege: ask for a read-only service account scoped to the tables/endpoints needed.
- Secrets live in env vars or a secret manager, never in code, tickets, chat or screenshots.
- Redact PII from logs, prompts and demo data. Use their sandbox, not production, to prototype.

Code demo below: a discovery checklist plus a risk register as dataclasses, printed as the
report you would attach to your scoping doc. Run: uv run python -m t08_forward_deployed.m_01_role_of_fde
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Phase(StrEnum):
    DISCOVERY = "discovery"
    SCOPING = "scoping"
    PROTOTYPE = "prototype"
    PRODUCTION = "production"
    HANDOFF = "handoff"


# What must be true before leaving each phase
EXIT_GATES: dict[Phase, list[str]] = {
    Phase.DISCOVERY: ["goal agreed", "data sources listed", "customer owner named"],
    Phase.SCOPING: ["scope doc signed off", "success metric defined", "risks reviewed"],
    Phase.PROTOTYPE: ["demo on sample data", "customer feedback captured"],
    Phase.PRODUCTION: ["security review passed", "monitoring live", "runbook drafted"],
    Phase.HANDOFF: ["customer ran it unaided", "docs delivered", "support path agreed"],
}


# Example 1: discovery checklist
@dataclass
class Question:
    topic: str
    ask: str
    answer: str | None = None  # None = still open

    @property
    def open(self) -> bool:
        return not self.answer


@dataclass
class Discovery:
    customer: str
    questions: list[Question] = field(default_factory=list)

    def open_questions(self) -> list[Question]:
        return [q for q in self.questions if q.open]


def starter_questions() -> list[Question]:
    return [
        Question("goal", "What business outcome does this integration drive, and who measures it?"),
        Question("data", "Which systems hold the data? Who owns each? Is there a sandbox?"),
        Question("volume", "How many records per day? Peak? How fresh must the data be?"),
        Question("auth", "How do we authenticate (API key, OAuth, SSO)? Who rotates credentials?"),
        Question("security", "What PII is involved? Where may it be processed? Who reviews us?"),
        Question("network", "Is the API public, behind a VPN, or IP-allowlisted?"),
        Question("ops", "Who is on call for this after handoff? What is their escalation path?"),
    ]


# Example 2: risk register (likelihood x impact on a 1..5 scale)
@dataclass
class Risk:
    name: str
    likelihood: int  # 1 (rare) .. 5 (almost certain)
    impact: int  # 1 (annoying) .. 5 (project fails)
    mitigation: str
    owner: str = "fde"

    @property
    def score(self) -> int:
        return self.likelihood * self.impact

    @property
    def level(self) -> str:
        return "HIGH" if self.score >= 15 else "MEDIUM" if self.score >= 8 else "LOW"


# Example 3: render the report (plain text you can paste into a scoping doc)
def render_report(discovery: Discovery, risks: list[Risk], phase: Phase) -> str:
    lines = [f"Engagement report: {discovery.customer}", f"Phase: {phase.value}", ""]
    lines.append(f"Open questions ({len(discovery.open_questions())}/{len(discovery.questions)}):")
    for q in discovery.questions:
        mark = " " if q.open else "x"
        lines.append(f"  [{mark}] {q.topic:<9} {q.ask}")
        if q.answer:
            lines.append(f"        -> {q.answer}")
    lines += ["", "Risk register (highest first):"]
    for r in sorted(risks, key=lambda r: (-r.score, r.name)):
        lines.append(f"  {r.level:<6} {r.score:>2}  {r.name} (owner: {r.owner})")
        lines.append(f"         mitigation: {r.mitigation}")
    lines += ["", f"Exit gate for '{phase.value}':"]
    lines += [f"  - {item}" for item in EXIT_GATES[phase]]
    return "\n".join(lines)


# Example 4: a status update in the same shape every week
def status_update(done: str, impact: str, next_step: str, eta: str) -> str:
    return f"Done: {done}\nImpact: {impact}\nNext: {next_step}\nETA: {eta}"


def run_demo() -> None:
    discovery = Discovery("Acme Logistics", starter_questions())
    discovery.questions[0].answer = "Cut invoice processing from 5 days to 1 (AP team lead)."
    discovery.questions[1].answer = "ERP REST API; sandbox exists; owner: j.rivera (IT)."
    risks = [
        Risk("Sandbox data differs from production", 4, 4, "Sample 1% of prod via read-only role"),
        Risk("API rate limit is 60 req/min", 3, 3, "Cache, backoff on 429, nightly bulk sync"),
        Risk(
            "Security review blocks launch", 2, 5, "Book review in week 1; share data-flow diagram"
        ),
        Risk("Customer owner changes roles", 2, 2, "Name a deputy; document in handoff"),
    ]
    print(render_report(discovery, risks, Phase.DISCOVERY))
    print()
    print(
        status_update(
            done="Read-only ERP key issued; first 200 invoices ingested in sandbox.",
            impact="Unblocks the extraction prototype.",
            next_step="Demo extraction accuracy on 50 invoices.",
            eta="Thursday",
        )
    )


"""
Common mistakes:
- Building before the goal and success metric are written down and agreed.
- Treating "the customer asked for it" as a requirement: ask what problem it solves.
- Heroics: becoming the only person who understands the integration (no handoff = no exit).
- Using production credentials or real customer data in a prototype or a screenshot.
- Hiding risk. A named, scored risk with an owner is a trust-building artifact.
- Quietly forking product behavior for one customer instead of feeding it back to product.

In the field:
- Keep a running decision log and a "things I learned" doc; both feed product feedback.
- Time-box discovery (days, not weeks) and ship a demo in week 1 to flush out wrong assumptions.
- Plan the handoff on day 1: who runs this, what they need to know, what breaks first.
- Before every call, know: the goal, the last commitment you made, and what you will ask for.
"""

if __name__ == "__main__":
    run_demo()
