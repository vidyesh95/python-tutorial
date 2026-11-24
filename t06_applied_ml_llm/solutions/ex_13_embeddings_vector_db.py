"""Reference solution for Exercise 13: Embeddings and vector search."""

import hashlib
import re
import sqlite3

import numpy as np


def chunk_text(text: str, size: int, overlap: int = 0) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    chunks: list[str] = []
    start = 0
    while words:
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
        start += size - overlap
    return chunks


def hashed_embedding(text: str, dim: int = 64) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        vec[int.from_bytes(digest, "big") % dim] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def cosine_top_k(query: np.ndarray, matrix: np.ndarray, k: int) -> list[tuple[int, float]]:
    q = np.asarray(query, dtype=float)
    m = np.asarray(matrix, dtype=float)
    denom = np.linalg.norm(m, axis=1) * np.linalg.norm(q)
    scores = np.divide(m @ q, denom, out=np.zeros(len(m)), where=denom > 0)
    order = np.argsort(-scores, kind="stable")[:k]
    return [(int(i), float(scores[i])) for i in order]


class SqliteVecIndex:
    def __init__(self, dim: int) -> None:
        import sqlite_vec

        self.db = sqlite3.connect(":memory:")
        self.db.enable_load_extension(True)
        sqlite_vec.load(self.db)
        self.db.enable_load_extension(False)
        self.db.execute(
            f"CREATE VIRTUAL TABLE items USING vec0(embedding float[{dim}] distance_metric=cosine)"
        )

    def add(self, item_id: int, vec: np.ndarray) -> None:
        import sqlite_vec

        self.db.execute(
            "INSERT INTO items(rowid, embedding) VALUES (?, ?)",
            (item_id, sqlite_vec.serialize_float32(np.asarray(vec, dtype=float).tolist())),
        )

    def search(self, query: np.ndarray, k: int = 3) -> list[tuple[int, float]]:
        import sqlite_vec

        rows = self.db.execute(
            "SELECT rowid, distance FROM items WHERE embedding MATCH ? AND k = ?",
            (sqlite_vec.serialize_float32(np.asarray(query, dtype=float).tolist()), k),
        ).fetchall()
        return [(int(rid), 1.0 - dist) for rid, dist in rows]
