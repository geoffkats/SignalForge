from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from signalforge_ml.features import build_feature_table
from signalforge_ml.ingest_lincs import ingest_lincs_csv


def train_baseline(config: dict) -> dict:
    dataset_config = config["dataset"]
    feature_config = config["features"]
    training_config = config["training"]
    artifact_config = config["artifacts"]

    frame = ingest_lincs_csv(
        dataset_config["input_path"],
        dataset_config["expected_columns"],
        dataset_config.get("checksum_sha256", ""),
    )
    features, labels, cleaned_frame = build_feature_table(
        frame,
        radius=feature_config["fingerprint_radius"],
        n_bits=feature_config["fingerprint_bits"],
    )

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=training_config["test_size"],
        random_state=training_config["random_state"],
        stratify=labels if len(np.unique(labels)) > 1 else None,
    )

    model = LogisticRegression(
        max_iter=training_config["logistic_max_iter"],
        class_weight=training_config.get("class_weight", "balanced"),
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    model_path = Path(artifact_config["model_path"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    processed_path = Path(dataset_config["processed_path"])
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_frame.to_parquet(processed_path, index=False)

    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    manifest = {
        "model_version": "baseline-logreg-v1",
        "algorithm": "Morgan fingerprint + hashed gene embedding + logistic regression",
        "artifact_path": str(model_path),
        "processed_dataset_path": str(processed_path),
        "metrics": report,
        "status": "trained",
    }

    manifest_path = Path(artifact_config["manifest_path"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest