"""Reference solution for Exercise 14: RAG building blocks."""

import re


def build_rag_prompt(question: str, chunks: list[dict[str, str]]) -> str:
    lines = [f"[{i}] ({c['source']}) {c['text']}" for i, c in enumerate(chunks, start=1)]
    sources = "\n".join(lines) if lines else "(no context found)"
    return (
        "Answer using ONLY the numbered sources below. Cite sources like [1] after each claim. "
        "If the sources do not contain the answer, reply exactly: I don't know.\n\n"
        f"Sources:\n{sources}\n\nQuestion: {question}"
    )


def extract_citations(answer: str) -> list[int]:
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def invalid_citations(answer: str, n_sources: int) -> list[int]:
    return [n for n in extract_citations(answer) if not 1 <= n <= n_sources]


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda item: -scores[item])  # sorted is stable: ties keep order


def hit_rate_and_mrr(
    ranked: list[list[str]], expected: list[str], k: int = 3
) -> tuple[float, float]:
    if not ranked:
        return 0.0, 0.0
    hits, reciprocal = 0, 0.0
    for results, want in zip(ranked, expected, strict=True):
        top = results[:k]
        if want in top:
            hits += 1
            reciprocal += 1 / (top.index(want) + 1)
    return hits / len(ranked), reciprocal / len(ranked)
