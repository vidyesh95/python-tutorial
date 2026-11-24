# scikit-learn Pipelines
"""
scikit-learn gives every model the same API: `fit(X, y)` learns, `predict(X)` applies,
`score(X, y)` measures. Transformers (scalers, encoders) use `fit` + `transform`.

Core ideas:
- SPLIT FIRST: `train_test_split(X, y, test_size=..., stratify=y, random_state=...)`. The test
  set is touched once, at the end. Stratify classification splits to keep class balance.
- LEAKAGE: fitting a scaler on ALL data lets test statistics leak into training. A `Pipeline`
  fits each step on the training fold only, so wrap preprocessing + model together.
- ColumnTransformer: different preprocessing per column group (scale numeric, one-hot
  categorical) inside the same pipeline.
- CROSS-VALIDATION: `cross_val_score(pipe, X, y, cv=5)` gives a distribution of scores, a
  more honest estimate than one split.
- METRICS: classification -> accuracy, precision/recall/F1 (use F1 or ROC-AUC when classes are
  imbalanced); regression -> MAE, RMSE, R^2.
- PERSISTENCE: `joblib.dump(pipe, path)` / `joblib.load(path)` (the whole pipeline, not just
  the model, so preprocessing travels with it).

Run: uv run python -m t06_applied_ml_llm.m_04_scikit_learn
"""

import tempfile
from pathlib import Path

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.datasets import make_classification, make_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 0


# Example: classification with a Pipeline (scaler + model) and holdout metrics
def classification_demo() -> Pipeline:
    X, y = make_classification(
        n_samples=400, n_features=6, n_informative=4, class_sep=1.5, random_state=SEED
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=SEED
    )
    pipe = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(max_iter=1000))])
    pipe.fit(X_train, y_train)  # scaler is fit on X_train only -> no leakage
    pred = pipe.predict(X_test)
    print(f"accuracy={accuracy_score(y_test, pred):.3f} f1={f1_score(y_test, pred):.3f}")
    scores = cross_val_score(pipe, X, y, cv=5)  # refits the whole pipeline per fold
    print(f"5-fold accuracy: {scores.mean():.3f} +/- {scores.std():.3f}")
    return pipe


# Example: regression comparing a linear model and a forest
def regression_demo() -> None:
    X, y = make_regression(n_samples=300, n_features=5, noise=10.0, random_state=SEED)
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=SEED)
    models = {
        "ridge": Pipeline([("scale", StandardScaler()), ("reg", Ridge(alpha=1.0))]),
        "forest": RandomForestRegressor(n_estimators=30, random_state=SEED),
    }
    for name, model in models.items():
        pred = model.fit(X_train, y_train).predict(X_test)
        print(
            f"{name}: MAE={mean_absolute_error(y_test, pred):.1f} R2={r2_score(y_test, pred):.3f}"
        )


# Example: mixed numeric + categorical columns with ColumnTransformer
def mixed_columns_demo() -> None:
    rng = np.random.default_rng(SEED)
    age = rng.integers(18, 70, size=200)
    plan = rng.choice(["free", "pro", "team"], size=200)
    X = np.column_stack([age, plan]).astype(object)  # column 0 numeric, column 1 categorical
    y = ((age > 40) | (plan == "pro")).astype(int)
    prep = ColumnTransformer(
        [("num", StandardScaler(), [0]), ("cat", OneHotEncoder(handle_unknown="ignore"), [1])]
    )
    pipe = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000))])
    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=SEED)
    print("mixed-columns accuracy:", round(pipe.fit(X_train, y_train).score(X_test, y_test), 3))


# Example: persist the fitted pipeline to a temp dir and reload it
def persistence_demo(pipe: Pipeline) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.joblib"
        joblib.dump(pipe, path)
        restored = joblib.load(path)  # only load files YOU produced: joblib uses pickle
        X = np.zeros((1, 6))
        print("same prediction after reload:", pipe.predict(X) == restored.predict(X))


"""
Common mistakes:
- Scaling/encoding before the split (data leakage) -> inflated test scores. Use a Pipeline.
- Tuning hyperparameters on the test set; use cross-validation or a separate validation set.
- Accuracy on imbalanced data (99% "no fraud" is 99% accurate and useless): use F1/ROC-AUC.
- Forgetting `random_state`, so results change between runs.
- `OneHotEncoder` without `handle_unknown="ignore"` crashing on a new category in production.
- Unpickling untrusted model files: joblib/pickle can execute arbitrary code on load.

Production notes:
- Pin the scikit-learn version with the saved model; artifacts are not guaranteed to load
  across versions. Store version + training data hash + metrics next to the file.
- Log the pipeline's input schema (column names/order); silent column reordering is a classic bug.
- Serve with a FastAPI endpoint (t04) that loads the model once at startup, not per request.
- Monitor input drift and live metrics; retrain on a schedule or when drift crosses a threshold.
- For hyperparameter search use `GridSearchCV`/`RandomizedSearchCV` (cross-validated by default).
"""

if __name__ == "__main__":
    fitted = classification_demo()
    regression_demo()
    mixed_columns_demo()
    persistence_demo(fitted)
