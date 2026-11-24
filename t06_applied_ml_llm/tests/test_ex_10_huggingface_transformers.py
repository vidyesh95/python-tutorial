import numpy as np
import pytest

from _loader import load

ex = load("t06_applied_ml_llm", "ex_10_huggingface_transformers")


@pytest.mark.parametrize(
    ("cuda", "mps", "expected"),
    [(True, False, "cuda"), (True, True, "cuda"), (False, True, "mps"), (False, False, "cpu")],
)
def test_pick_device(cuda, mps, expected):
    assert ex.pick_device(cuda, mps) == expected


def test_train_bpe_known_merges():
    assert ex.train_bpe(["aaab aaab"], 3) == [("a", "a"), ("a", "b"), ("aa", "ab")]


def test_train_bpe_weights_by_word_frequency():
    merges = ex.train_bpe(["low low low lower lowest"], 2)
    assert merges == [("l", "o"), ("lo", "w")]


def test_train_bpe_stops_when_nothing_left():
    assert ex.train_bpe(["ab"], 10) == [("a", "b")]
    assert ex.train_bpe([], 5) == []


def test_bpe_encode():
    merges = [("l", "o"), ("lo", "w")]
    assert ex.bpe_encode("lowest", merges) == ["low", "e", "s", "t"]
    assert ex.bpe_encode("xyz", merges) == ["x", "y", "z"]
    assert ex.bpe_encode("", merges) == []


def test_bpe_roundtrip_reconstructs_word():
    merges = ex.train_bpe(["new newer newest"], 5)
    assert "".join(ex.bpe_encode("newest", merges)) == "newest"


def test_filter_probs_top_k():
    out = ex.filter_probs(np.array([0.5, 0.3, 0.15, 0.05]), top_k=2)
    assert out == pytest.approx([0.625, 0.375, 0.0, 0.0])
    assert out.sum() == pytest.approx(1.0)


def test_filter_probs_top_p():
    out = ex.filter_probs(np.array([0.5, 0.3, 0.15, 0.05]), top_p=0.7)
    assert out == pytest.approx([0.625, 0.375, 0.0, 0.0])
    out = ex.filter_probs(np.array([0.1, 0.5, 0.4]), top_p=0.5)
    assert out == pytest.approx([0.0, 1.0, 0.0])


def test_filter_probs_noop_and_input_untouched():
    p = np.array([0.2, 0.3, 0.5])
    out = ex.filter_probs(p)
    assert out == pytest.approx(p)
    ex.filter_probs(p, top_k=1)
    assert p == pytest.approx([0.2, 0.3, 0.5])


def test_filter_probs_combined():
    out = ex.filter_probs(np.array([0.4, 0.3, 0.2, 0.1]), top_k=3, top_p=0.8)
    # after top_k=3: [4/9, 3/9, 2/9]; cumulative .444,.777,1.0 -> need all three for p=0.8
    assert (out > 0).sum() == 3
    assert out.sum() == pytest.approx(1.0)
