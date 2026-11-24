# Retrieval-Augmented Generation Pipeline
"""
RAG = give the model the facts it needs INSIDE the prompt, instead of hoping it memorized them.
It fixes the two big LLM problems for private/fresh data: no knowledge of your documents, and
confident made-up answers. Pipeline (each stage is a plain function you can test):

    ingest -> chunk -> embed -> store            (offline, once per document)
    question -> embed -> retrieve top-k -> rerank -> build prompt -> LLM -> answer + citations

- RETRIEVE: cheap, high-recall vector search (m_13) returns ~10-20 candidates.
- RERANK: a slower, more precise scorer reorders them and keeps the best ~3-5. Production uses
  a cross-encoder model (e.g. bge-reranker) or an LLM; here a tiny lexical re-scorer stands in.
- PROMPT: number every source [1], [2], ... and tell the model to cite those numbers and to say
  "I don't know" when the sources do not contain the answer.
- CITATIONS are checkable: parse the [n] markers from the answer and verify each points at a
  source you actually supplied (a cited-but-missing source is a hallucination signal).
- EVALUATE retrieval separately from generation: hit-rate@k (was the right source in the top
  k?) and MRR (how high was it?). Bad answers usually mean bad retrieval.

The LLM is a PLUGGABLE function `LLMFn = Callable[[str], str]`. By default a deterministic fake
answers from the retrieved text. With ANTHROPIC_API_KEY set, the same pipeline calls Claude.
Embeddings are the toy hashed bag-of-words from m_13 (swap in a real model for production).

Run: uv run python -m t06_applied_ml_llm.m_14_rag_pipeline
"""

import hashlib
import os
import re
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

LLMFn = Callable[[str], str]
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
DIM = 512


def embed(text: str) -> np.ndarray:
    vec = np.zeros(DIM, dtype=np.float32)
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        vec[int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "big") % DIM] += 1
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


@dataclass(frozen=True)
class Chunk:
    source: str
    index: int
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


# Example: ingest -> chunk -> embed -> store
def chunk_words(text: str, size: int = 40, overlap: int = 8) -> list[str]:
    words = text.split()
    out, start = [], 0
    while words:
        out.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
        start += size - overlap
    return out


class VectorStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.vectors: list[np.ndarray] = []

    def ingest(self, docs: dict[str, str], size: int = 40, overlap: int = 8) -> int:
        for source, text in docs.items():
            for i, part in enumerate(chunk_words(text, size, overlap)):
                self.chunks.append(Chunk(source, i, part))
                self.vectors.append(embed(part))
        return len(self.chunks)

    def retrieve(self, question: str, k: int = 6) -> list[Hit]:
        scores = np.stack(self.vectors) @ embed(question)
        return [
            Hit(self.chunks[i], float(scores[i])) for i in np.argsort(-scores, kind="stable")[:k]
        ]


# Example: rerank (stand-in for a cross-encoder): reward chunks covering more query terms
STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "of",
    "to",
    "in",
    "what",
    "how",
    "do",
    "does",
    "for",
    "and",
    "i",
}


def terms(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS}


def rerank(question: str, hits: list[Hit], keep: int = 3) -> list[Hit]:
    q = terms(question)
    rescored = [
        Hit(h.chunk, 0.5 * h.score + 0.5 * len(q & terms(h.chunk.text)) / max(len(q), 1))
        for h in hits
    ]
    return sorted(rescored, key=lambda h: -h.score)[:keep]


# Example: prompt with numbered sources
def build_prompt(question: str, hits: list[Hit]) -> str:
    sources = "\n".join(f"[{i}] ({h.chunk.source}) {h.chunk.text}" for i, h in enumerate(hits, 1))
    return (
        "Answer using ONLY the numbered sources below. Cite sources like [1] after each claim. "
        "If the sources do not contain the answer, reply exactly: I don't know.\n\n"
        f"Sources:\n{sources or '(no context found)'}\n\nQuestion: {question}\nAnswer:"
    )


def cited_numbers(answer: str) -> list[int]:
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", answer)})


def check_citations(answer: str, n_sources: int) -> list[int]:
    """Return citation numbers that point at a source that was never supplied."""
    return [n for n in cited_numbers(answer) if not 1 <= n <= n_sources]


# Example: pluggable LLMs
def fake_llm(prompt: str) -> str:
    """Deterministic stand-in: quote the source sentence that best overlaps the question."""
    question = prompt.rsplit("Question:", 1)[1].split("\nAnswer:")[0]
    best, best_overlap = "I don't know.", 0
    for line in prompt.split("Sources:\n", 1)[1].split("\n\nQuestion:")[0].splitlines():
        m = re.match(r"\[(\d+)\] \(.*?\) (.*)", line)
        if not m:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", m.group(2)):
            overlap = len(terms(question) & terms(sentence))
            if overlap > best_overlap:
                best, best_overlap = f"{sentence} [{m.group(1)}]", overlap
    return best


def claude_llm(prompt: str) -> str:
    import anthropic  # needs ANTHROPIC_API_KEY (read from the environment by the SDK)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system="You answer questions strictly from the provided sources and always cite them.",
        messages=[{"role": "user", "content": prompt}],
    )
    if message.stop_reason == "refusal":
        return "I don't know."
    return "".join(b.text for b in message.content if b.type == "text")


def answer(
    store: VectorStore, question: str, llm: LLMFn, min_score: float = 0.15
) -> tuple[str, list[Hit]]:
    hits = rerank(question, store.retrieve(question, k=6))
    if not hits or hits[0].score < min_score:  # abstain instead of letting the LLM guess
        return "I don't know.", []
    return llm(build_prompt(question, hits)), hits


# Example: evaluate retrieval with labeled questions
def hit_rate_and_mrr(
    store: VectorStore, labeled: list[tuple[str, str]], k: int = 3
) -> tuple[float, float]:
    hits_at_k, reciprocal = 0, 0.0
    for question, expected in labeled:
        sources = [h.chunk.source for h in store.retrieve(question, k=k)]
        if expected in sources:
            hits_at_k += 1
            reciprocal += 1 / (sources.index(expected) + 1)
    return hits_at_k / len(labeled), reciprocal / len(labeled)


DOCS = {
    "auth.md": "Nimbus uses API keys sent in the Authorization header as a Bearer token. "
    "Keys can be rotated from the dashboard and old keys stay valid for 24 hours after rotation.",
    "limits.md": "The free plan allows 60 requests per minute. The pro plan allows 600 requests per minute. "
    "When you exceed the limit the API returns HTTP 429 with a Retry-After header.",
    "billing.md": "Invoices are issued on the first day of each month. Usage is billed per 1000 requests "
    "and unused credits expire after 12 months.",
    "webhooks.md": "Nimbus signs every webhook with an HMAC SHA256 signature in the X-Nimbus-Signature header. "
    "Failed deliveries are retried five times with exponential backoff.",
}
EVAL_SET = [
    ("How are API keys sent to Nimbus?", "auth.md"),
    ("What is the request limit on the pro plan?", "limits.md"),
    ("When are invoices issued?", "billing.md"),
    ("How are webhook signatures verified?", "webhooks.md"),
]

"""
Common mistakes
- Stuffing the prompt with too many chunks: relevant text gets lost in the middle and cost grows.
- No abstain path: with weak retrieval the LLM happily invents an answer.
- Evaluating only the final answer. Measure retrieval (hit-rate, MRR) and generation separately.
- Ignoring prompt injection: retrieved text is UNTRUSTED. Delimit it, never let it change the
  system instructions, and do not give the model dangerous tools in the same call (m_15).
- Citations that are never verified: check that every [n] exists and ideally that the cited
  chunk actually supports the claim (an LLM-judge check, m_16).

Production notes
- Keep chunk metadata (source, page, URL, updated_at) so citations can link to the original.
- Re-ingest incrementally: hash each document and re-embed only what changed.
- Hybrid retrieval (BM25 keyword + vector, fused with reciprocal-rank fusion) beats either alone.
- Cache embeddings and, when the same big context is reused, use provider prompt caching (m_08).
- Log question, retrieved ids, scores, answer and citations; that log is your eval dataset.
"""

if __name__ == "__main__":
    store = VectorStore()
    print("ingested chunks:", store.ingest(DOCS, size=25, overlap=5))

    use_claude = bool(os.getenv("ANTHROPIC_API_KEY"))
    llm: LLMFn = claude_llm if use_claude else fake_llm
    print(
        "LLM:", f"Claude ({CLAUDE_MODEL})" if use_claude else "fake_llm (no ANTHROPIC_API_KEY set)"
    )

    for question, _ in EVAL_SET[:3]:
        reply, hits = answer(store, question, llm)
        print(f"\nQ: {question}\nA: {reply}")
        print(
            "   sources:",
            [f"[{i}] {h.chunk.source} ({h.score:.2f})" for i, h in enumerate(hits, 1)],
        )
        print("   bad citations:", check_citations(reply, len(hits)))

    reply, hits = answer(store, "What is the airspeed of a laden swallow?", llm)
    print("\nOff-topic question ->", reply, f"(sources used: {len(hits)})")

    hit_rate, mrr = hit_rate_and_mrr(store, EVAL_SET, k=3)
    print(f"\nretrieval eval: hit-rate@3 = {hit_rate:.2f}, MRR = {mrr:.2f}")
