"""Exercise 13: Embeddings and vector search.

Tasks
1. chunk_text(text, size, overlap): split on whitespace into word chunks of at most `size`
   words; each chunk starts `size - overlap` words after the previous one. Stop once a chunk
   reaches the last word (no trailing chunk that is a pure subset). overlap >= size raises
   ValueError. Empty/blank text -> [].  Chunks are joined with single spaces.
2. hashed_embedding(text, dim=64): deterministic bag-of-words vector. Tokens are
   re.findall(r"[a-z0-9]+", text.lower()). Token -> bucket =
   int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % dim;
   add 1.0 to that bucket. L2-normalize (an all-zero vector stays all zeros).
   Return a float32 numpy array of shape (dim,).
3. cosine_top_k(query, matrix, k): rows of `matrix` are document vectors (NOT necessarily
   normalized). Return up to k (row_index, cosine_similarity) tuples, best first; ties -> lower
   index first. A zero vector has similarity 0.0 (do not divide by zero).
4. SqliteVecIndex: a tiny vector index backed by sqlite-vec (in-memory SQLite, cosine metric).
   `add(item_id, vec)` stores a vector under an integer id; `search(query, k)` returns
   [(item_id, similarity)] best first, where similarity = 1 - cosine distance.
   Hints: see m_13 (`vec0` virtual table, `sqlite_vec.serialize_float32`, `embedding MATCH ?
   AND k = ?`). Needs: uv sync --group ml

Run: uv run pytest t06_applied_ml_llm -k ex_13
"""

import numpy as np


def chunk_text(text: str, size: int, overlap: int = 0) -> list[str]:
    raise NotImplementedError


def hashed_embedding(text: str, dim: int = 64) -> np.ndarray:
    raise NotImplementedError


def cosine_top_k(query: np.ndarray, matrix: np.ndarray, k: int) -> list[tuple[int, float]]:
    raise NotImplementedError


class SqliteVecIndex:
    def __init__(self, dim: int) -> None:
        raise NotImplementedError

    def add(self, item_id: int, vec: np.ndarray) -> None:
        raise NotImplementedError

    def search(self, query: np.ndarray, k: int = 3) -> list[tuple[int, float]]:
        raise NotImplementedError
