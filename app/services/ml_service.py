"""Load trusted repository artifacts once per application and score a customer."""

import json
from pathlib import Path

import joblib
import pandas as pd
from flask import current_app

from .schema import FEATURES


class ModelUnavailable(RuntimeError):
    pass


def model_bundle():
    if "churn_bundle" not in current_app.extensions:
        folder = Path(current_app.config["MODEL_DIR"])
        try:
            pipeline = joblib.load(folder / "churn_model.joblib")
            metadata = json.loads(
                (folder / "model_metrics.json").read_text(encoding="utf-8")
            )
            current_app.extensions["churn_bundle"] = (pipeline, metadata)
        except (OSError, ValueError, ImportError) as error:
            raise ModelUnavailable(
                "Model unavailable. Run python train_model.py to create the artifacts."
            ) from error
    return current_app.extensions["churn_bundle"]


def predict_customer(data):
    pipeline, metadata = model_bundle()
    frame = pd.DataFrame([{field: data[field] for field in FEATURES}])
    churn_index = list(pipeline.classes_).index(1)
    probability = float(pipeline.predict_proba(frame)[0, churn_index])
    return {
        "prediction": "Yes" if probability >= metadata["threshold"] else "No",
        "probability": probability,
        "model_version": metadata["model_version"],
    }
