"""Reference solution for Exercise 10: Hugging Face Transformers concepts."""

from collections import Counter

import numpy as np


def pick_device(cuda: bool, mps: bool) -> str:
    if cuda:
        return "cuda"
    return "mps" if mps else "cpu"


def _merge(symbols: tuple[str, ...], pair: tuple[str, str]) -> tuple[str, ...]:
    out: list[str] = []
    i = 0
    while i < len(symbols):
        if i + 1 < len(symbols) and (symbols[i], symbols[i + 1]) == pair:
            out.append(symbols[i] + symbols[i + 1])
            i += 2
        else:
            out.append(symbols[i])
            i += 1
    return tuple(out)


def train_bpe(corpus: list[str], num_merges: int) -> list[tuple[str, str]]:
    words: Counter[tuple[str, ...]] = Counter(tuple(w) for text in corpus for w in text.split())
    merges: list[tuple[str, str]] = []
    for _ in range(num_merges):
        pairs: Counter[tuple[str, str]] = Counter()
        for word, freq in words.items():
            for pair in zip(word, word[1:], strict=False):
                pairs[pair] += freq
        if not pairs:
            break
        top = max(pairs.values())
        best = min(p for p, c in pairs.items() if c == top)
        merges.append(best)
        merged: Counter[tuple[str, ...]] = Counter()
        for word, freq in words.items():
            merged[_merge(word, best)] += freq
        words = merged
    return merges


def bpe_encode(word: str, merges: list[tuple[str, str]]) -> list[str]:
    symbols = tuple(word)
    for pair in merges:
        symbols = _merge(symbols, pair)
    return list(symbols)


def filter_probs(
    probs: np.ndarray, top_k: int | None = None, top_p: float | None = None
) -> np.ndarray:
    p = np.asarray(probs, dtype=float).copy()
    if top_k is not None and top_k < len(p):
        p[np.argsort(-p, kind="stable")[top_k:]] = 0.0
        p /= p.sum()
    if top_p is not None:
        order = np.argsort(-p, kind="stable")
        cum = np.cumsum(p[order])
        cutoff = int(np.searchsorted(cum, top_p - 1e-9)) + 1
        p[order[cutoff:]] = 0.0
        p /= p.sum()
    return p
