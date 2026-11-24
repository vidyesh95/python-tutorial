"""Reference solution for Exercise 01: NumPy."""

import numpy as np


def standardize(x: np.ndarray) -> np.ndarray:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    safe_std = np.where(std == 0, 1.0, std)  # zero-variance column -> (x - mean) / 1 == 0
    return (x - mean) / safe_std


def moving_average(x: np.ndarray, k: int) -> np.ndarray:
    if k < 1 or k > len(x):
        raise ValueError("k must satisfy 1 <= k <= len(x)")
    csum = np.concatenate([[0.0], np.cumsum(x, dtype=float)])
    return (csum[k:] - csum[:-k]) / k


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    a_unit = a / np.where(a_norm == 0, 1.0, a_norm)  # zero rows stay zero -> similarity 0
    b_unit = b / np.where(b_norm == 0, 1.0, b_norm)
    return a_unit @ b_unit.T


def top_k_similar(query: np.ndarray, matrix: np.ndarray, k: int) -> np.ndarray:
    sims = cosine_similarity_matrix(query[None, :], matrix)[0]
    return np.argsort(-sims, kind="stable")[:k]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)
