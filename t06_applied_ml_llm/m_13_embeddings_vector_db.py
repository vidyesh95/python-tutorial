# Embeddings and Vector Databases
"""
An EMBEDDING maps text to a vector of floats so that texts with similar MEANING land close
together. Search then becomes geometry: embed the query, find the nearest stored vectors.

Similarity
- cosine similarity = (a . b) / (|a| |b|), range -1..1. If every vector is L2-normalized to
  length 1, cosine is just a dot product (fast: one matrix multiply scores everything).
- cosine DISTANCE = 1 - cosine similarity (what vector DBs usually return; smaller = closer).

Where embeddings come from (all need network or a local server, so this lesson fakes them)
- Gemini:   client.models.embed_content(model="gemini-embedding-001", contents=[...])
- Ollama:   ollama.Client().embed(model="nomic-embed-text", input=[...])   (m_11)
- Claude:   Anthropic offers no embeddings endpoint (its docs point to Voyage AI).
Rule: the SAME model must embed documents and queries; changing models means re-indexing.

Here we use a deterministic TOY embedding: hashed bag-of-words (each word is hashed to one of
`dim` buckets and counted, then L2-normalized). It only matches shared WORDS, not synonyms, but
it exercises the whole pipeline offline. Swap in a real model by replacing one function.

CHUNKING: models have input limits and a vector for a whole book is a blurry average. Split
documents into chunks (~100-400 words) with some OVERLAP so a fact cut at a boundary still
appears whole in one chunk.

VECTOR STORES
- Brute force (numpy): exact, perfectly fine up to ~100k vectors.
- sqlite-vec (used here): a SQLite extension; `vec0` virtual tables give KNN queries in SQL.
  We use it because chromadb and onnxruntime have no Python 3.15 wheels.
- pgvector (Postgres extension, overview only):
      CREATE EXTENSION vector;
      CREATE TABLE chunks (id bigserial PRIMARY KEY, body text, embedding vector(256));
      CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
      SELECT id, body FROM chunks ORDER BY embedding <=> $1 LIMIT 5;   -- <=> cosine distance
  Best choice when your data already lives in Postgres (t04 m_09): joins, transactions, backups.
- Approximate indexes (HNSW, IVF) trade a little recall for big speed at millions of vectors.

Run: uv run python -m t06_applied_ml_llm.m_13_embeddings_vector_db
"""

import hashlib
import re
import sqlite3
from collections.abc import Callable

import numpy as np

Embedder = Callable[[str], np.ndarray]


# Example: deterministic toy embedding (never use Python's hash(): it is randomized per run)
def hashed_embedding(text: str, dim: int = 256) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        bucket = (
            int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % dim
        )
        vec[bucket] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


# Example: cosine similarity and brute-force top-k
def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / denom) if denom else 0.0


def top_k(query: np.ndarray, matrix: np.ndarray, k: int) -> list[tuple[int, float]]:
    """Rows of `matrix` are unit vectors, so a matrix-vector product = all cosine scores."""
    scores = matrix @ query
    order = np.argsort(-scores, kind="stable")[:k]
    return [(int(i), float(scores[i])) for i in order]


# Example: chunking with overlap
def chunk_words(text: str, size: int = 50, overlap: int = 10) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    chunks: list[str] = []
    for start in range(0, max(len(words), 1), size - overlap):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return [c for c in chunks if c]


# Example: sqlite-vec KNN with a metadata filter
def open_vec_db(dim: int) -> sqlite3.Connection:
    import sqlite_vec  # optional dependency, imported lazily

    db = sqlite3.connect(":memory:")  # use a file path for persistence
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, source TEXT, body TEXT)")
    # `source` is a vec0 METADATA column: it can be used in the KNN WHERE clause.
    db.execute(
        f"CREATE VIRTUAL TABLE vec_chunks USING vec0("
        f"embedding float[{dim}] distance_metric=cosine, source text)"
    )
    return db


def insert_chunk(
    db: sqlite3.Connection, chunk_id: int, source: str, body: str, vec: np.ndarray
) -> None:
    import sqlite_vec

    db.execute("INSERT INTO chunks VALUES (?, ?, ?)", (chunk_id, source, body))
    db.execute(
        "INSERT INTO vec_chunks(rowid, embedding, source) VALUES (?, ?, ?)",
        (chunk_id, sqlite_vec.serialize_float32(vec.tolist()), source),
    )


def knn(
    db: sqlite3.Connection, query: np.ndarray, k: int = 3, source: str | None = None
) -> list[tuple[str, float]]:
    import sqlite_vec

    sql = "SELECT rowid, distance FROM vec_chunks WHERE embedding MATCH ? AND k = ?"
    params: list = [sqlite_vec.serialize_float32(query.tolist()), k]
    if source:
        sql += " AND source = ?"
        params.append(source)
    rows = db.execute(sql, params).fetchall()
    return [
        (db.execute("SELECT body FROM chunks WHERE id = ?", (rid,)).fetchone()[0], 1.0 - dist)
        for rid, dist in rows  # similarity = 1 - cosine distance
    ]


"""
Common mistakes
- Embedding queries and documents with DIFFERENT models (or dims): scores become meaningless.
- Not normalizing, then using dot product as if it were cosine.
- Chunks that are too big (vague vectors, wasted prompt tokens) or too small (no context).
- Trusting the top score absolutely: always keep a minimum-similarity threshold and be ready
  to answer "nothing relevant found".
- Re-embedding the whole corpus on every run: store vectors, embed incrementally by content hash.
- Using Python's built-in hash() for bucketing: it changes between processes.

Production notes
- Store metadata (source, page, timestamp, tenant id) with every chunk; filter BEFORE ranking
  for multi-tenant isolation (never post-filter another tenant's results).
- Version your embeddings (model name + dim in the table) so a model upgrade is a migration.
- Measure retrieval quality (hit rate, MRR) on labeled queries (m_14, m_16) before tuning chunk size.
- Exact search is simple and fast enough for most apps; add an ANN index only when you must.
"""

DOCS = {
    "pets.md": "Cats sleep most of the day. Dogs need daily walks and enjoy playing fetch outside.",
    "space.md": "The Moon orbits the Earth every 27 days. Mars has two small moons named Phobos and Deimos.",
    "cooking.md": "To boil pasta use salted water. Simmer tomato sauce slowly with garlic and basil.",
}

if __name__ == "__main__":
    # 1) similarity with the toy embedder
    a, b, c = (hashed_embedding(t) for t in ("the cat sat", "a cat sat down", "stock market crash"))
    print(f"cosine(cat sat, cat sat down)     = {cosine(a, b):.3f}")
    print(f"cosine(cat sat, stock market)     = {cosine(a, c):.3f}")

    # 2) chunking
    long_text = " ".join(f"w{i}" for i in range(23))
    print(
        "chunks:",
        [len(ch.split()) for ch in chunk_words(long_text, size=10, overlap=3)],
        "words each",
    )

    # 3) brute-force numpy search over all chunks
    labels, texts = [], []
    for name, body in DOCS.items():
        for part in chunk_words(body, size=8, overlap=2):
            labels.append(name)
            texts.append(part)
    matrix = np.stack([hashed_embedding(t) for t in texts])
    query = hashed_embedding("how often does the moon orbit")
    print("numpy top-2:", [(labels[i], round(s, 2)) for i, s in top_k(query, matrix, 2)])

    # 4) sqlite-vec KNN (skipped gracefully if the extension cannot load)
    try:
        db = open_vec_db(256)
        for i, (label, text) in enumerate(zip(labels, texts, strict=True), start=1):
            insert_chunk(db, i, label, text, matrix[i - 1])
        print("sqlite-vec top-2:", [(t[:28], round(s, 2)) for t, s in knn(db, query, 2)])
        print(
            "only cooking.md :",
            [(t[:28], round(s, 2)) for t, s in knn(db, query, 2, source="cooking.md")],
        )
    except (ImportError, AttributeError, sqlite3.OperationalError) as exc:
        print("sqlite-vec unavailable here:", exc)
