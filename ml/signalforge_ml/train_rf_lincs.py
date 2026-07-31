"""
train_rf_lincs.py
-----------------
RandomForest baseline for Phase 3 LINCS data.

Uses the exact same preprocessing as train_deep.py:
 - remove_conflicting_labels
 - compound vectors from LINCS SMILES
 - landmark GO gene vectors
 - abs(zscore) sample weights

This provides a fair baseline to beat with the dual-encoder net.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupShuffleSplit

from .train_deep import build_feature_matrix, remove_conflicting_labels

log = logging.getLogger(__name__)


def train_rf(config: dict) -> dict:
    dataset_config = config["dataset"]
    training_config = config["training"]
    artifact_config = config["artifacts"]

    input_path = Path(dataset_config["input_path"])
    log.info("Loading dataset from %s", input_path)
    df = pd.read_parquet(input_path)
    df = remove_conflicting_labels(df)

    # Subsample for a practical, reproducible RF baseline runtime.
    max_rows = int(training_config.get("rf_max_rows", 200_000))
    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=42)
        log.info("Subsampled to %d rows for RF baseline (memory efficiency)", len(df))

    # Do compound-level group split BEFORE building features to avoid OOM
    random_state = training_config.get("random_state", 42)
    test_size = training_config.get("test_size", 0.15)

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(df, df["label"], groups=df["pert_id"]))

    df_train = df.iloc[train_idx].reset_index(drop=True)
    df_test = df.iloc[test_idx].reset_index(drop=True)

    log.info(
        "Compound-level split: train=%d rows / %d compounds, test=%d rows / %d compounds",
        len(df_train),
        int(df_train["pert_id"].nunique()),
        len(df_test),
        int(df_test["pert_id"].nunique()),
    )

    # Build features separately for train and test to avoid OOM
    Xc_train, Xg_train, y_train, w_train, _ = build_feature_matrix(df_train)
    Xc_test, Xg_test, y_test, w_test, _ = build_feature_matrix(df_test)

    # Convert sparse compound features to dense for concatenation
    Xc_train_dense = Xc_train.toarray() if sparse.issparse(Xc_train) else Xc_train
    Xc_test_dense = Xc_test.toarray() if sparse.issparse(Xc_test) else Xc_test

    X_train = np.concatenate([Xc_train_dense, Xg_train], axis=1)
    X_test = np.concatenate([Xc_test_dense, Xg_test], axis=1)

    rf_n_estimators = int(training_config.get("rf_n_estimators", 200))
    rf_max_depth = training_config.get("rf_max_depth", 30)
    rf_min_samples_leaf = int(training_config.get("rf_min_samples_leaf", 2))
    rf_max_samples = training_config.get("rf_max_samples", 0.7)

    model = RandomForestClassifier(
        n_estimators=rf_n_estimators,
        max_features="sqrt",
        max_depth=rf_max_depth,
        min_samples_leaf=rf_min_samples_leaf,
        max_samples=rf_max_samples,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train, y_train, sample_weight=w_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    model_path = Path(artifact_config.get("rf_model_path", "artifacts/models/rf_lincs.joblib"))
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)

    manifest = {
        "model_version": "rf-lincs-v1",
        "algorithm": "RandomForest on Morgan-2048 + GO-1107",
        "rf_n_estimators": rf_n_estimators,
        "rf_max_depth": rf_max_depth,
        "rf_min_samples_leaf": rf_min_samples_leaf,
        "rf_max_samples": rf_max_samples,
        "rf_max_rows": max_rows,
        "artifact_path": str(model_path),
        "feature_width": int(X_train.shape[1]),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "n_compounds": int(df["pert_id"].nunique()),
        "n_genes": int(df["gene_symbol"].nunique()),
        "metrics": report,
        "accuracy": float(acc),
        "macro_f1": float(report.get("macro avg", {}).get("f1-score", 0.0)),
        "status": "trained",
    }

    manifest_path = Path(artifact_config.get("rf_manifest_path", "artifacts/manifests/rf_lincs_latest.json"))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    log.info("RF done: accuracy=%.4f macro_f1=%.4f", manifest["accuracy"], manifest["macro_f1"])
    return manifest


if __name__ == "__main__":
    import sys
    import yaml

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("configs/deep_lincs.yaml")
    config_path = config_path.resolve()
    config_root = config_path.parent.parent  # ml/ directory

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Resolve relative paths in config against the ml/ directory
    inp = Path(cfg["dataset"]["input_path"])
    if not inp.is_absolute():
        cfg["dataset"]["input_path"] = str(config_root / inp)

    m = train_rf(cfg)
    print(f"\nRF Accuracy : {m['accuracy']:.4f}")
    print(f"RF Macro F1 : {m['macro_f1']:.4f}")
