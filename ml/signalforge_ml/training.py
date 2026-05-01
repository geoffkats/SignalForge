from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from signalforge_ml.features import build_feature_table
from signalforge_ml.ingest_lincs import ingest_lincs_csv


def train_baseline(config: dict) -> dict:
    dataset_config = config["dataset"]
    feature_config = config["features"]
    training_config = config["training"]
    artifact_config = config["artifacts"]

    expected_cols = dataset_config["expected_columns"]
    # log2fc is optional — include if present in the CSV
    optional_cols = dataset_config.get("optional_columns", [])

    frame = ingest_lincs_csv(
        dataset_config["input_path"],
        expected_cols,
        dataset_config.get("checksum_sha256", ""),
        optional_columns=optional_cols,
    )

    features, labels, cleaned_frame = build_feature_table(
        frame,
        radius=feature_config["fingerprint_radius"],
        n_bits=feature_config["fingerprint_bits"],
        use_corr_selection=feature_config.get("use_corr_selection", True),
    )

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=training_config["test_size"],
        random_state=training_config["random_state"],
        stratify=labels if len(np.unique(labels)) > 1 else None,
    )

    # ------------------------------------------------------------------
    # Sample weights: weight each sample by |log2FC| so that strongly
    # regulated genes dominate training over weakly regulated ones.
    # Split weights with the same parameters so indices align.
    # ------------------------------------------------------------------
    sample_weight_train = None
    if "log2fc" in cleaned_frame.columns:
        w_all = cleaned_frame["log2fc"].abs().to_numpy(dtype=np.float64)
        w_all = w_all / (w_all.mean() + 1e-9)
        w_train, _ = train_test_split(
            w_all,
            test_size=training_config["test_size"],
            random_state=training_config["random_state"],
            stratify=labels if len(np.unique(labels)) > 1 else None,
        )
        sample_weight_train = w_train

    model = RandomForestClassifier(
        n_estimators=training_config.get("n_estimators", 300),
        max_depth=training_config.get("max_depth", None),
        min_samples_leaf=training_config.get("min_samples_leaf", 1),
        max_features=training_config.get("max_features", "sqrt"),
        class_weight="balanced",
        random_state=training_config["random_state"],
        n_jobs=-1,
    )
    model.fit(x_train, y_train, sample_weight=sample_weight_train)
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
        "algorithm": (
            "Morgan fingerprint (LNCAPcorr-selected bits) + "
            "LINCS L1000 GO-term gene fingerprint (978 genes x 1107 GO terms) + "
            "random forest"
        ),
        "sklearn_version": sklearn.__version__,
        "artifact_path": str(model_path),
        "processed_dataset_path": str(processed_path),
        "metrics": report,
        "status": "trained",
    }

    manifest_path = Path(artifact_config["manifest_path"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest