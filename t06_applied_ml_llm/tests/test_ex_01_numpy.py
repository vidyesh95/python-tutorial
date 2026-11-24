import pytest

pytest.importorskip("numpy")
import numpy as np

from _loader import load

ex = load("t06_applied_ml_llm", "ex_01_numpy")


def test_standardize_matches_reference():
    rng = np.random.default_rng(0)
    x = rng.normal(5, 3, size=(50, 4))
    z = ex.standardize(x)
    assert z.shape == x.shape
    np.testing.assert_allclose(z.mean(axis=0), 0, atol=1e-9)
    np.testing.assert_allclose(z.std(axis=0), 1, atol=1e-9)


def test_standardize_constant_column_is_zero_not_nan():
    x = np.array([[1.0, 7.0], [2.0, 7.0], [3.0, 7.0]])
    z = ex.standardize(x)
    assert not np.isnan(z).any()
    np.testing.assert_allclose(z[:, 1], 0)


def test_moving_average_values_and_length():
    out = ex.moving_average(np.array([1, 2, 3, 4, 5, 6]), 3)
    np.testing.assert_allclose(out, [2, 3, 4, 5])
    np.testing.assert_allclose(ex.moving_average(np.array([4.0, 8.0]), 1), [4, 8])


@pytest.mark.parametrize("k", [0, -1, 5])
def test_moving_average_bad_window(k):
    with pytest.raises(ValueError):
        ex.moving_average(np.array([1.0, 2.0, 3.0]), k)


def test_cosine_similarity_matrix_known_values():
    a = np.array([[1.0, 0.0], [1.0, 1.0]])
    b = np.array([[2.0, 0.0], [0.0, 3.0], [-1.0, 0.0]])
    out = ex.cosine_similarity_matrix(a, b)
    assert out.shape == (2, 3)
    np.testing.assert_allclose(out[0], [1.0, 0.0, -1.0], atol=1e-12)
    np.testing.assert_allclose(out[1, 0], np.sqrt(0.5))


def test_cosine_similarity_zero_vector_is_zero():
    out = ex.cosine_similarity_matrix(np.array([[0.0, 0.0]]), np.array([[1.0, 2.0]]))
    assert not np.isnan(out).any()
    assert out[0, 0] == 0.0


def test_top_k_similar_orders_by_similarity():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [0.9, 0.1], [-1.0, 0.0]])
    result = ex.top_k_similar(np.array([1.0, 0.0]), matrix, 3)
    assert list(result) == [0, 2, 1]


def test_softmax_rows_sum_to_one_and_is_stable():
    logits = np.array([[1000.0, 1001.0, 1002.0], [0.0, 0.0, 0.0]])
    out = ex.softmax(logits)
    assert not np.isnan(out).any()
    np.testing.assert_allclose(out.sum(axis=-1), 1.0)
    np.testing.assert_allclose(out[1], 1 / 3)
    assert out[0].argmax() == 2
