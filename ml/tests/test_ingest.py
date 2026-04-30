"""Tests for data ingestion and training CSV schema validation."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from signalforge_ml.ingest_lincs import ingest_lincs_csv

REQUIRED_COLS = [
    "perturbation_id",
    "compound_id",
    "compound_name",
    "smiles",
    "gene_symbol",
    "regulation_label",
]

LNCAP_CSV = (
    Path(__file__).parent.parent / "data" / "raw" / "deepcop" / "lncap_training.csv"
)


def _make_csv(tmp_path: Path, rows: list[dict]) -> Path:
    out = tmp_path / "test.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLS)
        writer.writeheader()
        writer.writerows(rows)
    return out


def _sample_row():
    return {
        "perturbation_id": "TEST_AR",
        "compound_id": "BRD-TEST",
        "compound_name": "Enzalutamide",
        "smiles": "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F",
        "gene_symbol": "AR",
        "regulation_label": "down",
    }


def test_ingest_returns_dataframe(tmp_path):
    csv_path = _make_csv(tmp_path, [_sample_row()])
    df = ingest_lincs_csv(csv_path, REQUIRED_COLS)
    assert isinstance(df, pd.DataFrame)


def test_ingest_all_required_columns_present(tmp_path):
    csv_path = _make_csv(tmp_path, [_sample_row()])
    df = ingest_lincs_csv(csv_path, REQUIRED_COLS)
    assert list(df.columns) == REQUIRED_COLS


def test_ingest_row_count_matches(tmp_path):
    rows = [_sample_row(), {**_sample_row(), "gene_symbol": "KLK3"}]
    csv_path = _make_csv(tmp_path, rows)
    df = ingest_lincs_csv(csv_path, REQUIRED_COLS)
    assert len(df) == 2


def test_ingest_missing_column_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("perturbation_id,smiles\nTEST,CC\n")
    with pytest.raises(ValueError, match="missing required columns"):
        ingest_lincs_csv(bad, REQUIRED_COLS)


def test_ingest_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        ingest_lincs_csv("/nonexistent/path/data.csv", REQUIRED_COLS)


def test_lncap_training_csv_exists_and_valid():
    if not LNCAP_CSV.exists():
        pytest.skip("lncap_training.csv not present")
    df = ingest_lincs_csv(LNCAP_CSV, REQUIRED_COLS)
    assert len(df) > 1000, "Expected at least 1000 LNCaP training rows"
    assert set(df["regulation_label"].unique()).issubset({"up", "down"})
