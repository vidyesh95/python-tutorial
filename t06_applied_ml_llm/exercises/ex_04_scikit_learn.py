"""Exercise 04: scikit-learn.

Tasks
1. split_data(X, y, test_size=0.25, seed=0): stratified train/test split with a fixed
   random_state. Return (X_train, X_test, y_train, y_test).
2. build_classifier_pipeline(): a Pipeline with two named steps: "scale" (StandardScaler) and
   "clf" (LogisticRegression with max_iter=1000). Preprocessing lives INSIDE the pipeline so the
   scaler is only ever fit on training data.
3. evaluate_classifier(pipe, X_test, y_test): return {"accuracy": float, "f1": float} for a
   FITTED pipeline (binary F1).
4. cross_val_mean(pipe, X, y, folds=5): mean accuracy across `folds`-fold cross-validation.
5. save_and_reload(pipe, path): persist the fitted pipeline with joblib to `path` (a Path),
   load it back and return the loaded pipeline.

Run: uv run pytest t06_applied_ml_llm -k ex_04
"""

from pathlib import Path

import numpy as np
from sklearn.pipeline import Pipeline


def split_data(
    X: np.ndarray, y: np.ndarray, test_size: float = 0.25, seed: int = 0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raise NotImplementedError


def build_classifier_pipeline() -> Pipeline:
    raise NotImplementedError


def evaluate_classifier(pipe: Pipeline, X_test: np.ndarray, y_test: np.ndarray) -> dict[str, float]:
    raise NotImplementedError


def cross_val_mean(pipe: Pipeline, X: np.ndarray, y: np.ndarray, folds: int = 5) -> float:
    raise NotImplementedError


def save_and_reload(pipe: Pipeline, path: Path) -> Pipeline:
    raise NotImplementedError
