"""Compare three pipelines on training folds and evaluate the winner once on holdout."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.services.schema import CATEGORIES, FEATURES, NUMERICAL
from config import BASE_DIR


def make_preprocessor():
    numeric = Pipeline(
        [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [("numeric", numeric, NUMERICAL), ("category", categorical, list(CATEGORIES))]
    )


def train(dataset_path, output_dir):
    frame = (
        pd.read_csv(dataset_path)
        .replace(r"^\s*$", np.nan, regex=True)
        .drop_duplicates()
    )
    missing = set(FEATURES + ["churn"]) - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    for field in NUMERICAL:
        frame[field] = pd.to_numeric(frame[field], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    for field, options in CATEGORIES.items():
        frame[field] = frame[field].where(frame[field].isin(options), np.nan)
    frame = frame.loc[frame.churn.isin(["Yes", "No"])].copy()
    if len(frame) < 1000 or frame.churn.value_counts().min() < 10:
        raise ValueError(
            "Training requires at least 1,000 labeled rows and both target classes."
        )
    X, y = frame[FEATURES], frame.churn.eq("Yes").astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    candidates = {
        "Logistic Regression": LogisticRegression(max_iter=1500, random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=180,
            max_depth=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=1,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=120, max_depth=2, learning_rate=0.06, random_state=42
        ),
    }
    results, pipelines = {}, {}
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    for name, estimator in candidates.items():
        pipeline = Pipeline(
            [("preprocess", make_preprocessor()), ("classifier", estimator)]
        )
        scores = cross_validate(
            pipeline,
            X_train,
            y_train,
            cv=folds,
            scoring={"f1": "f1", "accuracy": "accuracy", "roc_auc": "roc_auc"},
            n_jobs=1,
        )
        results[name] = {
            metric: float(scores[f"test_{metric}"].mean())
            for metric in ("f1", "accuracy", "roc_auc")
        }
        results[name]["f1_std"] = float(scores["test_f1"].std())
        pipelines[name] = pipeline
        print(
            f"{name:22} | CV F1: {results[name]['f1']:.4f} | CV accuracy: {results[name]['accuracy']:.4f}"
        )
    selected = max(results, key=lambda name: results[name]["f1"])
    pipeline = pipelines[selected].fit(X_train, y_train)
    probabilities = pipeline.predict_proba(X_test)[:, list(pipeline.classes_).index(1)]
    predictions = (probabilities >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
    }
    trained_at = datetime.now(timezone.utc).isoformat()
    digest = hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest()
    metadata = {
        "selected_algorithm": selected,
        "metrics": metrics,
        "candidates": results,
        "selection_method": "5-fold stratified cross-validation F1 on training data only",
        "dataset_size": len(frame),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "trained_at": trained_at,
        "random_seed": 42,
        "threshold": 0.5,
        "features": FEATURES,
        "dataset_sha256": digest,
        "model_version": f"{trained_at[:10]}-{digest[:12]}",
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "churn_rate": float(y.mean()),
        "confusion_matrix": confusion_matrix(
            y_test, predictions, labels=[0, 1]
        ).tolist(),
        "classification_report": classification_report(
            y_test,
            predictions,
            target_names=["Stay", "Churn"],
            output_dict=True,
            zero_division=0,
        ),
        "limitations": "Synthetic data only. Probabilities are model estimates, not calibrated real-world churn rates. No causal explanations or fairness guarantees.",
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_dir / "churn_model.joblib", compress=3)
    joblib.dump(
        pipeline.named_steps["preprocess"],
        output_dir / "preprocessor.joblib",
        compress=3,
    )
    (output_dir / "model_metrics.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    pd.DataFrame(
        metadata["confusion_matrix"],
        index=["Actual stay", "Actual churn"],
        columns=["Predicted stay", "Predicted churn"],
    ).to_csv(output_dir / "confusion_matrix.csv")
    print(f"\nSelected: {selected}\nHeld-out test metrics:")
    for metric, value in metrics.items():
        print(f"  {metric:10}: {value:.4f}")
    print(
        classification_report(
            y_test, predictions, target_names=["Stay", "Churn"], zero_division=0
        )
    )
    print("Confusion matrix [Stay, Churn]:", metadata["confusion_matrix"])
    # The checked-in README stays aligned when the model is retrained.
    readme = BASE_DIR / "README.md"
    if readme.exists():
        content = readme.read_text(encoding="utf-8")
        start, end = "<!-- MODEL_METRICS_START -->", "<!-- MODEL_METRICS_END -->"
        if start in content and end in content:
            table = f"\nSelected algorithm: **{selected}**. Training: **{len(X_train):,}** rows; held-out test: **{len(X_test):,}** rows.\n\n| Test metric | Value |\n| --- | ---: |\n"
            table += "".join(
                f"| {key.replace('_', ' ').title()} | {value:.2%} |\n"
                for key, value in metrics.items()
            )
            table += f"\nGenerated from `models/model_metrics.json`. Trained on {trained_at[:10]} (UTC).\n\n"
            readme.write_text(
                content.split(start)[0] + start + table + end + content.split(end)[1],
                encoding="utf-8",
            )
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=BASE_DIR / "data" / "customer_churn.csv"
    )
    parser.add_argument("--output", type=Path, default=BASE_DIR / "models")
    args = parser.parse_args()
    train(args.data, args.output)
