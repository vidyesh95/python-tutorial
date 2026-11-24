# NumPy Arrays and Vectorization
"""
NumPy's `ndarray` is a fixed-type, contiguous block of numbers. Operations run in C over the
whole block ("vectorized"), which is 10-100x faster than a Python `for` loop. Nearly every ML
library (pandas, scikit-learn, PyTorch, embeddings code) is built on this model.

Core ideas:
- SHAPE: tuple of axis lengths, e.g. (3, 4) = 3 rows, 4 columns. `reshape` changes the view.
- DTYPE: one type per array (`float64`, `float32`, `int64`, `bool`). float32 halves memory and
  is what GPUs and embedding models use; mixing types silently upcasts.
- BROADCASTING: shapes are compared from the right; each pair of axes must be equal or 1 (or
  missing). (3, 4) + (4,) works (row added to every row); (3, 4) + (3,) fails, use (3, 1).
- VIEWS vs COPIES: slices are views (writes change the original); fancy/boolean indexing copies.
- LINEAR ALGEBRA: `@` is matrix multiply, `np.linalg.norm`, `np.linalg.solve`.
- COSINE SIMILARITY: dot(a, b) / (|a||b|). The standard way to compare embedding vectors
  (lesson 13), and a neat showcase of broadcasting + matmul.

Run: uv run python -m t06_applied_ml_llm.m_01_numpy
"""

import time

import numpy as np

rng = np.random.default_rng(42)  # seeded generator: the modern replacement for np.random.seed


# Example: creating arrays, shapes, dtypes
def creation_demo() -> None:
    a = np.array([1, 2, 3])  # int64 by default
    b = np.arange(12).reshape(3, 4)  # 0..11 as 3 rows x 4 cols
    z = np.zeros((2, 3), dtype=np.float32)
    print(a.dtype, b.shape, b.ndim, z.dtype, z.nbytes, "bytes")
    print(np.linspace(0, 1, 5))  # 5 evenly spaced points, endpoints included
    print((a / 2).dtype, (a * 2).dtype)  # true division always gives float


# Example: broadcasting + boolean masks + axis reductions
def broadcasting_demo() -> None:
    m = np.arange(12, dtype=float).reshape(3, 4)
    col_means = m.mean(axis=0)  # shape (4,): collapse rows -> one value per column
    centered = m - col_means  # (3, 4) - (4,) broadcasts across rows
    print(centered.mean(axis=0))  # ~0 for every column
    row_sums = m.sum(axis=1, keepdims=True)  # (3, 1): keepdims makes row-wise division work
    print((m / np.maximum(row_sums, 1)).round(2))
    mask = m > 5  # boolean array, same shape
    print(m[mask])  # boolean indexing returns a 1-D COPY of matches
    print(np.where(m % 2 == 0, "even", "odd")[0])  # vectorized if/else


# Example: vectorized vs loop (the reason NumPy exists)
def vectorization_demo() -> None:
    x = rng.random(200_000)
    start = time.perf_counter()
    loop_total = 0.0
    for v in x:
        loop_total += v * v
    loop_s = time.perf_counter() - start
    start = time.perf_counter()
    vec_total = float(x @ x)  # dot product with itself = sum of squares
    vec_s = time.perf_counter() - start
    print(
        f"loop {loop_s * 1e3:.1f} ms | vectorized {vec_s * 1e3:.3f} ms | same: {np.isclose(loop_total, vec_total)}"
    )


# Example: linear algebra
def linear_algebra_demo() -> None:
    a = np.array([[3.0, 1.0], [1.0, 2.0]])
    b = np.array([9.0, 8.0])
    x = np.linalg.solve(a, b)  # solve a @ x = b (never invert the matrix by hand)
    print(x, np.allclose(a @ x, b))
    print(np.linalg.norm(b), (a.T @ a).shape)


# Example: cosine similarity between embedding-like vectors
def cosine_matrix(queries: np.ndarray, docs: np.ndarray) -> np.ndarray:
    """(n, d) x (m, d) -> (n, m) cosine similarities, via normalize-then-matmul."""
    q = queries / np.linalg.norm(queries, axis=1, keepdims=True)
    d = docs / np.linalg.norm(docs, axis=1, keepdims=True)
    return q @ d.T


def similarity_demo() -> None:
    docs = rng.normal(size=(5, 8)).astype(np.float32)  # pretend: 5 document embeddings
    query = docs[2:3] + 0.1 * rng.normal(size=(1, 8))  # a noisy copy of document 2
    sims = cosine_matrix(query, docs)[0]
    print(sims.round(2), "-> best match:", int(np.argmax(sims)))
    print("top 3:", np.argsort(-sims)[:3])  # argsort ascending, so negate for descending


"""
Common mistakes:
- Python loops over array elements; reach for slicing, `where`, `sum(axis=...)` first.
- Forgetting `axis`: `m.sum()` collapses everything; `m.sum(axis=0)` is per column.
- Broadcasting surprises: (n,) vs (n, 1) behave very differently; print `.shape` often.
- Mutating a slice and being surprised the original changed (it is a view); use `.copy()`.
- Comparing floats with `==`; use `np.isclose` / `np.allclose`.
- Dividing by a zero norm in cosine similarity (zero vectors) -> NaN; guard with `np.maximum`.
- Integer overflow in small dtypes (`uint8` wraps at 255) and silent int -> float upcasts.

Production notes:
- Memory: float32 embeddings are half the size of float64; 1M x 768 float32 = ~3 GB.
- Preallocate (`np.empty`) instead of growing arrays in a loop; `np.concatenate` copies.
- For huge similarity searches use a vector index (lesson 13) instead of an (n, m) matrix.
- Always seed with `np.random.default_rng(seed)` so experiments are reproducible.
- `np.save` / `np.load` for fast binary arrays; avoid pickle for untrusted data.
"""

if __name__ == "__main__":
    creation_demo()
    broadcasting_demo()
    vectorization_demo()
    linear_algebra_demo()
    similarity_demo()
