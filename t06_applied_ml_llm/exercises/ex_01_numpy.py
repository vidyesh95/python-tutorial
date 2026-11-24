"""Exercise 01: NumPy.

Implement each function with vectorized NumPy (no Python loops over elements).

Tasks
1. standardize(x): column-wise z-score of a 2-D array, (x - mean) / std along axis 0.
   A column with zero std becomes all zeros (no NaN / divide-by-zero).
2. moving_average(x, k): 1-D simple moving average, "valid" positions only (length n-k+1).
   Raise ValueError if k < 1 or k > len(x). Hint: cumulative sum.
3. cosine_similarity_matrix(a, b): (n, d) x (m, d) -> (n, m). Rows with zero norm give
   similarity 0 against everything (never NaN).
4. top_k_similar(query, matrix, k): indices of the k rows of `matrix` most cosine-similar to
   the 1-D `query`, most similar first.
5. softmax(logits): numerically stable softmax over the LAST axis (subtract the max first).

Run: uv run pytest t06_applied_ml_llm -k ex_01
"""

import numpy as np


def standardize(x: np.ndarray) -> np.ndarray:
    raise NotImplementedError


def moving_average(x: np.ndarray, k: int) -> np.ndarray:
    raise NotImplementedError


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    raise NotImplementedError


def top_k_similar(query: np.ndarray, matrix: np.ndarray, k: int) -> np.ndarray:
    raise NotImplementedError


def softmax(logits: np.ndarray) -> np.ndarray:
    raise NotImplementedError
