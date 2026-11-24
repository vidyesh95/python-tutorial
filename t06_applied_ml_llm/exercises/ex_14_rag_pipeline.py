"""Exercise 14: RAG building blocks (no LLM, no network).

Tasks
1. build_rag_prompt(question, chunks): `chunks` is a list of {"source": str, "text": str}.
   Return one prompt string that
   - tells the model to answer ONLY from the sources, to cite them like [1], and to reply
     "I don't know" when the answer is missing (use the words "cite" and "I don't know"),
   - lists every chunk on its own line as `[N] (source) text` with N starting at 1,
   - ends with the question (it must appear in the prompt),
   - shows the line `(no context found)` in place of the sources when `chunks` is empty.
2. extract_citations(answer): the sorted list of unique integers found in `[n]` markers.
   "A [2], B [1][2]" -> [1, 2]. No markers -> [].
3. invalid_citations(answer, n_sources): the sorted cited numbers that are NOT in 1..n_sources.
4. reciprocal_rank_fusion(rankings, k=60): merge several ranked id lists (best first). Each id
   scores sum(1 / (k + rank)) over the lists it appears in (rank starts at 1). Return ids
   sorted by score descending; ties keep first-seen order.
5. hit_rate_and_mrr(ranked, expected, k=3): ranked[i] is the ranked id list for query i and
   expected[i] the id that should be found. hit-rate = fraction of queries whose expected id is
   in the first k; MRR = mean of 1/rank (rank within the first k, else 0). Empty -> (0.0, 0.0).

Run: uv run pytest t06_applied_ml_llm -k ex_14
"""


def build_rag_prompt(question: str, chunks: list[dict[str, str]]) -> str:
    raise NotImplementedError


def extract_citations(answer: str) -> list[int]:
    raise NotImplementedError


def invalid_citations(answer: str, n_sources: int) -> list[int]:
    raise NotImplementedError


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> list[str]:
    raise NotImplementedError


def hit_rate_and_mrr(
    ranked: list[list[str]], expected: list[str], k: int = 3
) -> tuple[float, float]:
    raise NotImplementedError
