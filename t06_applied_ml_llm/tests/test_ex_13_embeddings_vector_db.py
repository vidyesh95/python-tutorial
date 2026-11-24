import numpy as np
import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_13_embeddings_vector_db")


def test_chunk_text_overlap():
    text = " ".join(str(i) for i in range(10))
    assert ex.chunk_text(text, size=4, overlap=1) == ["0 1 2 3", "3 4 5 6", "6 7 8 9"]


def test_chunk_text_no_overlap_and_short():
    assert ex.chunk_text("a b c d e", size=2) == ["a b", "c d", "e"]
    assert ex.chunk_text("a b", size=10) == ["a b"]


def test_chunk_text_empty_and_invalid():
    assert ex.chunk_text("   ", size=3) == []
    with pytest.raises(ValueError):
        ex.chunk_text("a b c", size=3, overlap=3)


def test_hashed_embedding_properties():
    v = ex.hashed_embedding("The cat sat", dim=64)
    assert v.shape == (64,) and v.dtype == np.float32
    assert np.linalg.norm(v) == pytest.approx(1.0, abs=1e-6)
    assert np.allclose(v, ex.hashed_embedding("sat cat THE!", dim=64))  # order/case/punct-free


def test_hashed_embedding_counts_repeats():
    v = ex.hashed_embedding("a a b", dim=4096)
    assert sorted(v[v > 0]) == pytest.approx([1 / np.sqrt(5), 2 / np.sqrt(5)], abs=1e-5)


def test_hashed_embedding_empty_is_zero():
    assert not ex.hashed_embedding("!!!", dim=16).any()


def test_hashed_embedding_related_texts_closer():
    q = ex.hashed_embedding("moon orbit period", dim=512)
    near = ex.hashed_embedding("the moon has an orbit", dim=512)
    far = ex.hashed_embedding("pasta with tomato sauce", dim=512)
    assert q @ near > q @ far


def test_cosine_top_k_ranks_and_scores():
    matrix = np.array([[1.0, 0.0], [0.0, 2.0], [1.0, 1.0], [0.0, 0.0]])
    out = ex.cosine_top_k(np.array([1.0, 0.0]), matrix, k=3)
    assert [i for i, _ in out] == [0, 2, 1]
    assert out[0][1] == pytest.approx(1.0)
    assert out[1][1] == pytest.approx(2**-0.5)
    assert out[2][1] == pytest.approx(0.0)


def test_cosine_top_k_zero_vector_and_k_larger_than_rows():
    matrix = np.array([[0.0, 0.0], [1.0, 0.0]])
    out = ex.cosine_top_k(np.array([1.0, 0.0]), matrix, k=10)
    assert out == [(1, pytest.approx(1.0)), (0, 0.0)]


def test_cosine_top_k_tie_prefers_lower_index():
    matrix = np.array([[1.0, 0.0], [2.0, 0.0]])
    assert [i for i, _ in ex.cosine_top_k(np.array([1.0, 0.0]), matrix, 2)] == [0, 1]


def test_sqlite_vec_index():
    pytest.importorskip("sqlite_vec")
    idx = ex.SqliteVecIndex(dim=3)
    idx.add(10, np.array([1.0, 0.0, 0.0]))
    idx.add(20, np.array([0.0, 1.0, 0.0]))
    idx.add(30, np.array([0.7, 0.7, 0.0]))
    hits = idx.search(np.array([1.0, 0.0, 0.0]), k=2)
    assert [i for i, _ in hits] == [10, 30]
    assert hits[0][1] == pytest.approx(1.0, abs=1e-5)
    assert hits[1][1] == pytest.approx(2**-0.5, abs=1e-3)
