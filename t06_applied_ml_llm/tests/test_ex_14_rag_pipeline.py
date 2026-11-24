import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_14_rag_pipeline")

CHUNKS = [
    {"source": "limits.md", "text": "The pro plan allows 600 requests per minute."},
    {"source": "auth.md", "text": "Keys are sent as a Bearer token."},
]


def test_prompt_numbers_sources_and_includes_question():
    prompt = ex.build_rag_prompt("What is the pro limit?", CHUNKS)
    assert "[1] (limits.md) The pro plan allows 600 requests per minute." in prompt
    assert "[2] (auth.md) Keys are sent as a Bearer token." in prompt
    assert "What is the pro limit?" in prompt
    assert prompt.index("[1]") < prompt.index("[2]") < prompt.rindex("What is the pro limit?")


def test_prompt_contains_instructions():
    prompt = ex.build_rag_prompt("q", CHUNKS).lower()
    assert "cite" in prompt
    assert "i don't know" in prompt


def test_prompt_without_context():
    prompt = ex.build_rag_prompt("Anything?", [])
    assert "(no context found)" in prompt
    assert "Anything?" in prompt
    assert "[1]" not in prompt.split("Sources:")[1]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Pro is 600/min [1].", [1]),
        ("A [2], B [1][2]", [1, 2]),
        ("No sources cited.", []),
        ("Index a[0] and list [x] are not citations but [10] is.", [0, 10]),
    ],
)
def test_extract_citations(answer, expected):
    assert ex.extract_citations(answer) == expected


def test_invalid_citations():
    assert ex.invalid_citations("see [1] and [4] and [0]", 3) == [0, 4]
    assert ex.invalid_citations("see [1][2]", 2) == []
    assert ex.invalid_citations("nothing", 2) == []


def test_rrf_orders_by_combined_rank():
    fused = ex.reciprocal_rank_fusion([["a", "b", "c"], ["b", "c", "d"]])
    assert fused[0] == "b"  # rank 2 + rank 1 beats a's single rank 1
    assert set(fused) == {"a", "b", "c", "d"}
    assert fused.index("c") < fused.index("d")


def test_rrf_ties_keep_first_seen_order():
    assert ex.reciprocal_rank_fusion([["x", "y"], ["y", "x"]]) == ["x", "y"]


def test_rrf_single_list_and_empty():
    assert ex.reciprocal_rank_fusion([["a", "b"]]) == ["a", "b"]
    assert ex.reciprocal_rank_fusion([]) == []


def test_hit_rate_and_mrr():
    ranked = [["a", "b", "c"], ["x", "y", "z"], ["p", "q", "r", "s"]]
    expected = ["a", "z", "s"]
    hit, mrr = ex.hit_rate_and_mrr(ranked, expected, k=3)
    assert hit == pytest.approx(2 / 3)  # "s" is rank 4, outside k=3
    assert mrr == pytest.approx((1 + 1 / 3 + 0) / 3)


def test_hit_rate_and_mrr_empty_and_larger_k():
    assert ex.hit_rate_and_mrr([], []) == (0.0, 0.0)
    hit, mrr = ex.hit_rate_and_mrr([["p", "q", "r", "s"]], ["s"], k=4)
    assert (hit, mrr) == (1.0, 0.25)
