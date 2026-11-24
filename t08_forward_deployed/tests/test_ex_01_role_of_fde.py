import pytest

from _loader import load

ex = load("t08_forward_deployed", "ex_01_role_of_fde")


def test_risk_score_and_level():
    assert ex.risk_score(3, 4) == 12
    assert ex.risk_level(15) == "HIGH"
    assert ex.risk_level(14) == "MEDIUM"
    assert ex.risk_level(8) == "MEDIUM"
    assert ex.risk_level(7) == "LOW"


@pytest.mark.parametrize("bad", [(0, 3), (3, 6), (-1, 2)])
def test_risk_score_rejects_out_of_range(bad):
    with pytest.raises(ValueError):
        ex.risk_score(*bad)


def test_risk_score_rejects_non_int():
    with pytest.raises(ValueError):
        ex.risk_score(2.5, 3)


def test_top_risks_order_ties_and_no_mutation():
    risks = [
        ex.Risk("b", 2, 2),
        ex.Risk("a", 2, 2),
        ex.Risk("big", 5, 5),
        ex.Risk("mid", 3, 3),
    ]
    snapshot = list(risks)
    assert [r.name for r in ex.top_risks(risks, 3)] == ["big", "mid", "a"]
    assert risks == snapshot
    assert ex.top_risks(risks, 0) == []
    assert len(ex.top_risks(risks, 10)) == 4


def test_open_topics():
    answers = {"goal": "ship", "auth": None, "data": "   ", "ops": "", "network": "vpn"}
    assert ex.open_topics(answers) == ["auth", "data", "ops"]


def test_next_phase_requires_all_gate_items():
    P = ex.Phase
    assert ex.next_phase(P.DISCOVERY, {"goal agreed"}) == P.DISCOVERY
    assert ex.next_phase(P.DISCOVERY, {"goal agreed", "data sources listed"}) == P.SCOPING
    assert ex.next_phase(P.PROTOTYPE, {"demo done", "extra"}) == P.PRODUCTION
    assert ex.next_phase(P.HANDOFF, {"customer ran it unaided"}) == P.HANDOFF


def test_format_status_update():
    text = ex.format_status_update(" Shipped ingest ", "Unblocks demo", "Review", "Thu")
    assert text == "Done: Shipped ingest\nImpact: Unblocks demo\nNext: Review\nETA: Thu"


def test_format_status_update_rejects_empty():
    with pytest.raises(ValueError):
        ex.format_status_update("x", "  ", "y", "z")
