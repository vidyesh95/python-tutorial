"""Reference solution for Exercise 16: LLM evaluation metrics."""

import json
import re


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold()).rstrip(".!?")


def exact_match(pred: str, gold: str) -> bool:
    return _normalize(pred) == _normalize(gold)


def regex_match(pred: str, pattern: str) -> bool:
    return re.search(pattern, pred.strip(), re.IGNORECASE) is not None


def percentile(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("percentile of empty list")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p / 100
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def diff_runs(old: dict[str, bool], new: dict[str, bool]) -> dict[str, list[str]]:
    regressions = sorted(i for i, ok in new.items() if not ok and old.get(i) is True)
    fixes = sorted(i for i, ok in new.items() if ok and not old.get(i, False))
    return {"regressions": regressions, "fixes": fixes}


def parse_judge_score(raw: str) -> int | None:
    if m := re.search(r"\{.*?\}", raw, re.DOTALL):
        try:
            return max(1, min(5, int(json.loads(m.group(0))["score"])))
        except ValueError, KeyError, TypeError:
            pass
    if m := re.search(r"score\D{0,3}(\d)", raw, re.IGNORECASE):
        return max(1, min(5, int(m.group(1))))
    return None
