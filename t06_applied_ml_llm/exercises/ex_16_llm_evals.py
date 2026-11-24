"""Exercise 16: LLM evaluation metrics (pure Python, no model calls).

Tasks
1. exact_match(pred, gold): normalize BOTH (strip, casefold, collapse runs of whitespace to one
   space, drop trailing '.', '!' or '?' characters) then compare.
   exact_match("  Paris.  ", "paris") is True.
2. regex_match(pred, pattern): True when `re.search(pattern, pred.strip(), re.IGNORECASE)`
   finds a match.
3. percentile(values, p): the p-th percentile (0-100) with linear interpolation between
   closest ranks (what numpy.percentile does by default). Empty input raises ValueError.
4. diff_runs(old, new): both map case id -> passed (bool). Return
   {"regressions": [...], "fixes": [...]} with sorted ids. A regression passed in `old` and
   fails in `new`. A fix passes in `new` and failed in `old` OR did not exist in `old`.
   Ids missing from `new` are ignored.
5. parse_judge_score(raw): extract a 1-5 score from an LLM judge reply.
   - If the text contains a JSON object (first "{...}") with a "score" key, use int(score);
     it may be a string like "4".
   - Otherwise look for "score" followed by a digit (e.g. "Score: 3/5" -> 3), case-insensitive.
   - Clamp the result into 1..5. If nothing can be parsed return None (never guess).

Run: uv run pytest t06_applied_ml_llm -k ex_16
"""


def exact_match(pred: str, gold: str) -> bool:
    raise NotImplementedError


def regex_match(pred: str, pattern: str) -> bool:
    raise NotImplementedError


def percentile(values: list[float], p: float) -> float:
    raise NotImplementedError


def diff_runs(old: dict[str, bool], new: dict[str, bool]) -> dict[str, list[str]]:
    raise NotImplementedError


def parse_judge_score(raw: str) -> int | None:
    raise NotImplementedError
