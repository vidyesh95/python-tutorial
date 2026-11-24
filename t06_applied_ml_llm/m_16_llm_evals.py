# LLM Evaluation
"""
"It looks good" is not a test. LLM outputs are non-deterministic and prompts change often, so
you need EVALS: a fixed dataset, automatic graders, and numbers you can compare across versions.

1. GOLDEN DATASET: 20-200 real, representative cases in JSONL: id, input, expected output (or
   a regex/rubric), category. Add every production bug as a new case. Never grade on cases you
   tuned the prompt against only; keep a held-out slice.
2. GRADERS (cheapest first)
   - exact match (normalized): classification, extraction, yes/no
   - regex / contains: required format or keywords ("order id ORD-\\d+")
   - semantic similarity: embedding cosine vs a reference answer, with a threshold
   - code-based checks: valid JSON, schema, unit tests, citation validity (m_14)
   - LLM-AS-JUDGE: another model scores open-ended answers against a rubric. Cheap and scalable
     but biased (prefers long answers, its own style, the first option). Use a clear rubric,
     ask for JSON, and CALIBRATE: measure agreement with human labels before trusting it.
3. METRICS: pass rate overall and per category, plus latency (p50/p95), tokens and COST per run.
4. REGRESSION TRACKING: store each run (prompt version, model, per-case results). Diff against
   the previous run: which cases newly FAIL (regressions) vs newly pass (fixes). Gate merges on
   "no regressions in critical categories and pass rate >= baseline - tolerance".

Everything here is offline: the "model" is a deterministic fake and the judge is a fake that
scores by keyword overlap. With ANTHROPIC_API_KEY set, `claude_judge` (Claude Haiku 5.5) can be
plugged in through the same `Judge` function type.
Run: uv run python -m t06_applied_ml_llm.m_16_llm_evals
"""

import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-haiku-5-5")  # cheap model is fine as a judge
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}  # $/MTok in/out


@dataclass
class Response:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float


Model = Callable[[str], Response]
Judge = Callable[[str, str, str], str]  # (question, reference, answer) -> raw judge text


# Example: golden dataset as JSONL (written to a temp dir; never into the repo)
CASES = [
    {"id": "m1", "category": "math", "input": "What is 7 * 6?", "expected": "42"},
    {"id": "m2", "category": "math", "input": "What is 100 / 4?", "expected": "25"},
    {"id": "f1", "category": "facts", "input": "Capital of France?", "expected": "Paris"},
    {"id": "f2", "category": "facts", "input": "Capital of Japan?", "expected": "Tokyo"},
    {"id": "f3", "category": "facts", "input": "Largest planet?", "expected": "Jupiter"},
    {
        "id": "r1",
        "category": "format",
        "input": "Give an order id for Ada",
        "pattern": r"^ORD-\d{4}$",
    },
    {
        "id": "r2",
        "category": "format",
        "input": "Give an order id for Bob",
        "pattern": r"^ORD-\d{4}$",
    },
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# Example: graders
def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold()).rstrip(".!?")


def exact_match(pred: str, gold: str) -> bool:
    return normalize(pred) == normalize(gold)


def regex_match(pred: str, pattern: str) -> bool:
    return re.search(pattern, pred.strip(), re.IGNORECASE) is not None


def embed(text: str, dim: int = 256) -> np.ndarray:
    vec = np.zeros(dim)
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        vec[int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "big") % dim] += 1
    n = np.linalg.norm(vec)
    return vec / n if n else vec


def semantic_match(pred: str, gold: str, threshold: float = 0.6) -> bool:
    return float(embed(pred) @ embed(gold)) >= threshold


def grade(case: dict, answer: str) -> bool:
    if "pattern" in case:
        return regex_match(answer, case["pattern"])
    return exact_match(answer, case["expected"])


# Example: LLM-as-judge (fake judge + robust parsing of its output)
JUDGE_RUBRIC = (
    "Score the ANSWER against the REFERENCE from 1 (wrong) to 5 (fully correct). "
    'Reply with JSON only: {"score": <1-5>, "reason": "<short>"}'
)


def fake_judge(question: str, reference: str, answer: str) -> str:
    overlap = len(set(normalize(reference).split()) & set(normalize(answer).split()))
    score = 5 if overlap == len(set(normalize(reference).split())) else 3 if overlap else 1
    return f'Sure! {{"score": {score}, "reason": "keyword overlap {overlap}"}}'


def claude_judge(question: str, reference: str, answer: str) -> str:
    import anthropic  # needs ANTHROPIC_API_KEY

    msg = anthropic.Anthropic().messages.create(
        model=JUDGE_MODEL,
        max_tokens=200,
        system=JUDGE_RUBRIC,
        messages=[
            {
                "role": "user",
                "content": f"QUESTION: {question}\nREFERENCE: {reference}\nANSWER: {answer}",
            }
        ],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def parse_judge_score(raw: str) -> int | None:
    """Judges ramble. Pull the JSON object (or 'score: N') out and clamp to 1-5."""
    if m := re.search(r"\{.*?\}", raw, re.DOTALL):
        try:
            return max(1, min(5, int(json.loads(m.group(0))["score"])))
        except ValueError, KeyError, TypeError:
            pass
    if m := re.search(r"score\D{0,3}(\d)", raw, re.IGNORECASE):
        return max(1, min(5, int(m.group(1))))
    return None  # unparseable: count as a judge failure, never as a pass


def judge_agreement(judge: Judge, labeled: list[tuple[str, str, str, bool]]) -> float:
    """Calibration: fraction of human labels (question, reference, answer, is_good) the judge matches."""
    hits = 0
    for q, ref, ans, human_good in labeled:
        score = parse_judge_score(judge(q, ref, ans))
        hits += score is not None and (score >= 4) == human_good
    return hits / len(labeled)


# Example: fake models = two prompt versions of the system under test
def make_model(version: str, seed: int = 0) -> Model:
    answers_v1 = {
        "m1": "42",
        "m2": "24",
        "f1": "Paris.",
        "f2": "Kyoto",
        "f3": "jupiter",
        "r1": "ORD-1234",
        "r2": "ORD-77",
    }
    answers_v2 = {
        "m1": "42",
        "m2": "25",
        "f1": "Paris",
        "f2": "Tokyo",
        "f3": "Saturn",
        "r1": "ORD-1234",
        "r2": "ORD-5678",
    }
    table = answers_v1 if version == "v1" else answers_v2
    rng = np.random.default_rng(seed)
    ids = {c["input"]: c["id"] for c in CASES}

    def model(prompt: str) -> Response:
        text = table[ids[prompt]]
        return Response(
            text, len(prompt.split()) * 2, len(text.split()) + 1, float(rng.gamma(4.0, 0.15))
        )

    return model


# Example: run, summarize, diff
def run_eval(model: Model, cases: list[dict]) -> list[dict]:
    rows = []
    for case in cases:
        resp = model(case["input"])
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "passed": grade(case, resp.text),
                **asdict(resp),
            }
        )
    return rows


def percentile(values: list[float], p: float) -> float:
    return float(np.percentile(values, p))


def cost_usd(rows: list[dict], model_name: str) -> float:
    price_in, price_out = PRICES[model_name]
    return (
        sum(r["input_tokens"] * price_in + r["output_tokens"] * price_out for r in rows) / 1_000_000
    )


def summarize(rows: list[dict]) -> dict:
    by_cat: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r["passed"])
    lat = [r["latency_s"] for r in rows]
    return {
        "pass_rate": sum(r["passed"] for r in rows) / len(rows),
        "by_category": {c: sum(v) / len(v) for c, v in sorted(by_cat.items())},
        "latency_p50": percentile(lat, 50),
        "latency_p95": percentile(lat, 95),
        "tokens": sum(r["input_tokens"] + r["output_tokens"] for r in rows),
    }


def diff_runs(old: list[dict], new: list[dict]) -> dict[str, list[str]]:
    before = {r["id"]: r["passed"] for r in old}
    after = {r["id"]: r["passed"] for r in new}
    return {
        "regressions": sorted(i for i in after if before.get(i) and not after[i]),
        "fixes": sorted(i for i in after if after[i] and not before.get(i, False)),
    }


def gate(old: list[dict], new: list[dict], tolerance: float = 0.0) -> tuple[bool, str]:
    d = diff_runs(old, new)
    drop = summarize(old)["pass_rate"] - summarize(new)["pass_rate"]
    if drop > tolerance:
        return False, f"pass rate dropped by {drop:.0%}"
    if d["regressions"]:
        return False, f"regressions: {d['regressions']}"
    return True, "ok"


"""
Common mistakes
- A dataset of 5 hand-picked easy cases: pass rate 100% means nothing. Include hard and weird ones.
- Grading with the same model that wrote the answer, or an unscored judge. Calibrate the judge.
- Comparing runs that differ in more than one thing (prompt AND model AND temperature).
- Only looking at the average: a +5% mean can hide a critical-category regression. Diff per case.
- Ignoring flakiness: run non-deterministic cases several times and report the pass fraction.
- Treating an unparseable judge reply as a pass.

Production notes
- Run evals in CI on every prompt/model change; store results (JSON per run) as build artifacts.
- Keep cost and latency next to quality: a 1% gain for 3x cost is often a bad trade.
- Grow the dataset from production logs and user thumbs-down (with privacy review).
- Anthropic's `/claude-api build-eval` and the Console evaluation tool can help bootstrap datasets.
"""

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "golden.jsonl"
        write_jsonl(path, CASES)
        cases = read_jsonl(path)
        print(f"loaded {len(cases)} golden cases from JSONL")

        v1, v2 = run_eval(make_model("v1"), cases), run_eval(make_model("v2", seed=1), cases)
        for name, rows in (("v1", v1), ("v2", v2)):
            s = summarize(rows)
            print(
                f"{name}: pass={s['pass_rate']:.0%} by_category={ {k: round(v, 2) for k, v in s['by_category'].items()} } "
                f"p50={s['latency_p50']:.2f}s p95={s['latency_p95']:.2f}s tokens={s['tokens']} "
                f"cost(opus-5.5)=${cost_usd(rows, 'claude-opus-5-5'):.5f} cost(haiku-5.5)=${cost_usd(rows, 'claude-haiku-5-5'):.6f}"
            )
        print("diff v1 -> v2:", diff_runs(v1, v2))
        print("gate v1 -> v2:", gate(v1, v2))
        (Path(tmp) / "run_v2.json").write_text(
            json.dumps(v2)
        )  # history lives in files/DB, not memory

    print(
        "semantic 'The capital is Paris' vs 'Paris':",
        semantic_match("The capital is Paris", "Paris", 0.5),
    )
    judge: Judge = claude_judge if os.getenv("ANTHROPIC_API_KEY") else fake_judge
    print(
        "judge:",
        "Claude " + JUDGE_MODEL
        if judge is claude_judge
        else "fake_judge (no ANTHROPIC_API_KEY set)",
    )
    raw = judge("Capital of France?", "Paris", "The capital of France is Paris")
    print("judge raw:", raw, "-> score", parse_judge_score(raw))
    labeled = [
        ("Capital of France?", "Paris", "Paris", True),
        ("Capital of France?", "Paris", "Lyon", False),
        ("Largest planet?", "Jupiter", "It is Jupiter", True),
    ]
    print(f"judge/human agreement: {judge_agreement(judge, labeled):.0%}")
