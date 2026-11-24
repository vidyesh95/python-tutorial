"""Exercise 10: Hugging Face Transformers concepts (offline).

Implement tokenization and decoding helpers without downloading any model.

Tasks
1. pick_device(cuda, mps): return "cuda" if cuda else "mps" if mps else "cpu".
2. train_bpe(corpus, num_merges): toy byte-pair encoding. Split every text on whitespace; each
   word starts as a tuple of single characters. Repeat `num_merges` times: count adjacent
   symbol pairs over all words (weighted by how often the word occurs), merge the most frequent
   pair everywhere (ties: the lexicographically smallest pair), record it. Stop early if no
   pairs remain. Return the list of merges, e.g. [("l", "o"), ("lo", "w")].
3. bpe_encode(word, merges): start from the word's characters and apply every merge IN ORDER
   (left to right inside the word). Return the list of tokens.
   e.g. bpe_encode("lowest", [("l","o"), ("lo","w")]) -> ["low", "e", "s", "t"]
4. filter_probs(probs, top_k=None, top_p=None): numpy array in, numpy array out.
   First keep only the `top_k` highest probabilities (ties: lower index wins), renormalize.
   Then keep the smallest set of highest-probability tokens whose cumulative mass reaches
   `top_p`, renormalize. Dropped entries become exactly 0. Output sums to 1.

Run: uv run pytest t06_applied_ml_llm -k ex_10
"""

import numpy as np


def pick_device(cuda: bool, mps: bool) -> str:
    raise NotImplementedError


def train_bpe(corpus: list[str], num_merges: int) -> list[tuple[str, str]]:
    raise NotImplementedError


def bpe_encode(word: str, merges: list[tuple[str, str]]) -> list[str]:
    raise NotImplementedError


def filter_probs(
    probs: np.ndarray, top_k: int | None = None, top_p: float | None = None
) -> np.ndarray:
    raise NotImplementedError
