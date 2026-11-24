"""Reference solution for Exercise 04: scikit-learn."""

from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def split_data(
    X: np.ndarray, y: np.ndarray, test_size: float = 0.25, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return train_test_split(X, y, test_size=test_size, stratify=y, random_state=seed)


def build_classifier_pipeline() -> Pipeline:
    return Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])


def evaluate_classifier(pipe: Pipeline, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, float]:
    pred = pipe.predict(X_test)
    return {"accuracy": float(accuracy_score(y_test, pred)), "f1": float(f1_score(y_test, pred))}


def cross_val_mean(pipe: Pipeline, X: np.ndarray, y: np.ndarray, folds: int = 5) -> float:
    return float(cross_val_score(pipe, X, y, cv=folds).mean())


def save_and_reload(pipe: Pipeline, path: Path) -> Pipeline:
    joblib.dump(pipe, path)
    return joblib.load(path)
