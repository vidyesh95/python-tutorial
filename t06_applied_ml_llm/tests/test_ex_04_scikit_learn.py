import numpy as np
import pytest

pytest.importorskip("sklearn")
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from _loader import load

ex = load("t06_applied_ml_llm", "ex_04_scikit_learn")


@pytest.fixture(scope="module")
def data():
    X, y = make_classification(
        n_samples=300,
        n_features=6,
        n_informative=4,
        class_sep=2.0,
        weights=[0.7, 0.3],
        random_state=0,
    )
    return X * np.array([1, 10, 100, 1, 1, 1]), y  # unscaled columns make scaling matter


def test_split_is_stratified_reproducible_and_complete(data):
    X, y = data
    X_tr, X_te, y_tr, y_te = ex.split_data(X, y, test_size=0.2, seed=3)
    assert len(X_tr) + len(X_te) == len(X) and len(y_te) == len(X_te)
    assert len(X_te) == 60
    assert y_tr.mean() == pytest.approx(y.mean(), abs=0.02)  # stratified
    again = ex.split_data(X, y, test_size=0.2, seed=3)
    np.testing.assert_array_equal(X_te, again[1])


def test_pipeline_structure(data):
    pipe = ex.build_classifier_pipeline()
    assert isinstance(pipe, Pipeline)
    assert [name for name, _ in pipe.steps] == ["scale", "clf"]
    assert isinstance(pipe.named_steps["scale"], StandardScaler)
    assert isinstance(pipe.named_steps["clf"], LogisticRegression)
    assert pipe.named_steps["clf"].max_iter == 1000


def test_evaluate_classifier_matches_sklearn_metrics(data):
    from sklearn.metrics import accuracy_score, f1_score

    X, y = data
    X_tr, X_te, y_tr, y_te = ex.split_data(X, y)
    pipe = ex.build_classifier_pipeline().fit(X_tr, y_tr)
    metrics = ex.evaluate_classifier(pipe, X_te, y_te)
    pred = pipe.predict(X_te)
    assert set(metrics) == {"accuracy", "f1"}
    assert metrics["accuracy"] == pytest.approx(accuracy_score(y_te, pred))
    assert metrics["f1"] == pytest.approx(f1_score(y_te, pred))
    assert metrics["accuracy"] > 0.8


def test_cross_val_mean(data):
    X, y = data
    pipe = ex.build_classifier_pipeline()
    expected = cross_val_score(ex.build_classifier_pipeline(), X, y, cv=4).mean()
    assert ex.cross_val_mean(pipe, X, y, folds=4) == pytest.approx(expected)


def test_save_and_reload_roundtrip(data, tmp_path):
    X, y = data
    pipe = ex.build_classifier_pipeline().fit(X, y)
    path = tmp_path / "model.joblib"
    loaded = ex.save_and_reload(pipe, path)
    assert path.exists()
    assert loaded is not pipe
    np.testing.assert_array_equal(loaded.predict(X), pipe.predict(X))
