import json

import joblib
import numpy as np
import pandas as pd

from app.services.schema import DEFAULTS, FEATURES, SERVICE_ADDONS
from config import BASE_DIR
from generate_data import generate_dataset


def test_synthetic_generation_reproducible_and_coherent():
    frame = generate_dataset(1000, seed=8)
    pd.testing.assert_frame_equal(frame, generate_dataset(1000, seed=8))
    assert len(frame) >= 1000
    assert list(frame.columns) == FEATURES + ["churn"]
    no_internet = frame.internet_service.eq("No")
    assert (frame.loc[no_internet, SERVICE_ADDONS] == "No internet service").all().all()
    assert (
        frame.loc[frame.phone_service.eq("No"), "multiple_lines"]
        .eq("No phone service")
        .all()
    )
    assert 0.1 < frame.churn.eq("Yes").mean() < 0.6


def test_pipeline_handles_missing_and_unseen_category():
    model = joblib.load(BASE_DIR / "models" / "churn_model.joblib")
    frame = pd.DataFrame(
        [{**DEFAULTS, "monthly_charges": np.nan, "contract": "New category"}]
    )[FEATURES]
    output = model.predict_proba(frame)
    assert output.shape == (1, 2)
    assert np.isfinite(output).all()
    assert np.isclose(output.sum(), 1)


def test_saved_metrics_match_holdout_predictions():
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split

    metadata = json.loads((BASE_DIR / "models" / "model_metrics.json").read_text())
    frame = pd.read_csv(BASE_DIR / "data" / "customer_churn.csv").drop_duplicates()
    target = frame.churn.eq("Yes").astype(int)
    _, test, _, expected = train_test_split(
        frame[FEATURES], target, test_size=0.2, stratify=target, random_state=42
    )
    model = joblib.load(BASE_DIR / "models" / "churn_model.joblib")
    predicted = model.predict(test)
    assert np.isclose(
        accuracy_score(expected, predicted), metadata["metrics"]["accuracy"]
    )
    assert np.isclose(f1_score(expected, predicted), metadata["metrics"]["f1"])
    assert sum(map(sum, metadata["confusion_matrix"])) == metadata["test_size"]
    assert metadata["train_size"] + metadata["test_size"] == len(frame)
