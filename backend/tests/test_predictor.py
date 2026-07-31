"""Unit tests for predictor manifest loading, atlas, and heuristic fallback."""
from __future__ import annotations

import json

import pytest

from app.services.predictor import SignalForgePredictor, _extract_key_metrics


def test_extract_metrics_accuracy():
    raw = {"accuracy": 0.55, "macro avg": {"f1-score": 0.51}, "weighted avg": {"f1-score": 0.53}}
    m = _extract_key_metrics(raw)
    assert m["accuracy"] == 0.55


def test_extract_metrics_macro_f1():
    raw = {"accuracy": 0.55, "macro avg": {"f1-score": 0.51}, "weighted avg": {"f1-score": 0.53}}
    m = _extract_key_metrics(raw)
    assert m["macro_f1"] == 0.51


def test_extract_metrics_returns_empty_for_non_dict():
    assert _extract_key_metrics("bad input") == {}


def test_extract_metrics_handles_missing_fields():
    m = _extract_key_metrics({"accuracy": 0.6})
    assert "accuracy" in m
    assert "macro_f1" not in m


def test_predictor_loads_manifest_from_file(tmp_path):
    manifest = {
        "model_version": "test-v1",
        "algorithm": "test algo",
        "status": "trained",
        "metrics": {"accuracy": 0.60, "macro avg": {"f1-score": 0.55}, "weighted avg": {"f1-score": 0.57}},
    }
    p = tmp_path / "latest.json"
    p.write_text(json.dumps(manifest))
    predictor = SignalForgePredictor(
        model_version="fallback",
        manifest_path=str(p),
        model_artifact_path=str(tmp_path / "missing.joblib"),
        eager_load=True,
    )
    assert predictor.manifest.model_version == "test-v1"
    assert predictor.manifest.training_status == "trained"
    assert predictor.manifest.training_metrics["accuracy"] == 0.60
    assert predictor.inference_mode == "heuristic"


def test_predictor_fallback_when_manifest_missing():
    predictor = SignalForgePredictor(
        model_version="fallback-v0",
        manifest_path="/nonexistent/path.json",
        model_artifact_path="/nonexistent/model.joblib",
        eager_load=True,
    )
    assert predictor.manifest.model_version == "fallback-v0"
    assert predictor.manifest.training_metrics == {}
    assert predictor.inference_mode == "heuristic"


def test_predictor_loads_atlas_from_fixture(tmp_path):
    atlas = {
        "version": "test",
        "n_compounds": 2,
        "compounds": [
            {"compound_id": "C1", "compound_name": "DrugA", "smiles": "CCO"},
            {"compound_id": "C2", "compound_name": "DrugB", "smiles": "CCN"},
        ],
    }
    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(atlas))
    predictor = SignalForgePredictor(
        model_version="heuristic",
        model_artifact_path=str(tmp_path / "missing.joblib"),
        compound_atlas_path=str(path),
        eager_load=True,
    )
    assert predictor.atlas_size == 2
    ranked = predictor.reverse_signature_search(["MYC"], ["TP53"], top_k=2)
    assert len(ranked) == 2
    assert {r.compound_id for r in ranked} == {"C1", "C2"}


def test_predictor_invalid_smiles_raises():
    predictor = SignalForgePredictor(
        model_version="heuristic",
        model_artifact_path="/nonexistent/model.joblib",
        eager_load=True,
    )
    # Without RDKit this may pass through; with RDKit it must raise.
    try:
        from signalforge_ml.inference import validate_smiles  # noqa: F401
    except ImportError:
        pytest.skip("signalforge_ml / RDKit not installed in backend test env")
    with pytest.raises(ValueError):
        predictor.predict_gene_effects("not-a-smiles%%%", ["AR"])


def test_predictor_heuristic_predict_returns_correct_count():
    predictor = SignalForgePredictor(
        model_version="heuristic",
        model_artifact_path="/nonexistent/model.joblib",
        eager_load=True,
    )
    genes = ["AR", "KLK3", "PTEN"]
    results = predictor._heuristic_predict("CC", genes)
    assert len(results) == len(genes)


def test_predictor_heuristic_direction_valid():
    predictor = SignalForgePredictor(
        model_version="heuristic",
        model_artifact_path="/nonexistent/model.joblib",
        eager_load=True,
    )
    results = predictor._heuristic_predict("CC", ["AR", "EZH2", "MYC", "PTEN"])
    for r in results:
        assert r.direction in ("up", "down", "neutral")


def test_predictor_heuristic_probabilities_sum_to_one():
    predictor = SignalForgePredictor(
        model_version="heuristic",
        model_artifact_path="/nonexistent/model.joblib",
        eager_load=True,
    )
    results = predictor._heuristic_predict("CC", ["AR"])
    r = results[0]
    assert abs(r.up_probability + r.down_probability - 1.0) < 1e-4


def test_predictor_heuristic_deterministic():
    predictor = SignalForgePredictor(
        model_version="heuristic",
        model_artifact_path="/nonexistent/model.joblib",
        eager_load=True,
    )
    r1 = predictor._heuristic_predict("CC", ["AR"])[0]
    r2 = predictor._heuristic_predict("CC", ["AR"])[0]
    assert r1.up_probability == r2.up_probability
