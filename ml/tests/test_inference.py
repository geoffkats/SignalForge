"""Integration tests for SignalForgeModel — requires baseline.joblib to be present."""
from __future__ import annotations

from pathlib import Path

import pytest

MODEL_PATH = Path(__file__).parent.parent / "artifacts" / "models" / "baseline.joblib"
ENZALUTAMIDE = "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"


@pytest.fixture(scope="module")
def model():
    if not MODEL_PATH.exists():
        pytest.skip("baseline.joblib not found — run `signalforge-ml train` first")
    from signalforge_ml.inference import SignalForgeModel
    return SignalForgeModel(model_path=MODEL_PATH)


def test_model_loads(model):
    assert model is not None


def test_predict_genes_returns_one_score_per_gene(model):
    genes = ["AR", "KLK3", "PTEN", "EZH2"]
    scores = model.predict_genes(ENZALUTAMIDE, genes)
    assert len(scores) == len(genes)


def test_predict_genes_symbols_preserved(model):
    genes = ["AR", "KLK3", "PTEN"]
    scores = model.predict_genes(ENZALUTAMIDE, genes)
    returned = [s.gene for s in scores]
    assert returned == genes


def test_predict_genes_probabilities_sum_to_one(model):
    scores = model.predict_genes(ENZALUTAMIDE, ["AR"])
    s = scores[0]
    assert abs(s.up_prob + s.down_prob - 1.0) < 1e-4


def test_predict_genes_probabilities_in_range(model):
    scores = model.predict_genes(ENZALUTAMIDE, ["AR", "KLK3", "PTEN"])
    for s in scores:
        assert 0.0 <= s.up_prob <= 1.0
        assert 0.0 <= s.down_prob <= 1.0


def test_predict_genes_direction_valid_values(model):
    scores = model.predict_genes(ENZALUTAMIDE, ["AR", "KLK3", "PTEN", "EZH2"])
    for s in scores:
        assert s.direction in ("up", "down", "neutral")


def test_predict_genes_confidence_is_max_prob(model):
    scores = model.predict_genes(ENZALUTAMIDE, ["AR"])
    s = scores[0]
    assert s.confidence == round(max(s.up_prob, s.down_prob), 4)


def test_predict_genes_different_compounds_differ(model):
    s1 = model.predict_genes(ENZALUTAMIDE, ["AR"])[0]
    s2 = model.predict_genes(ASPIRIN, ["AR"])[0]
    assert s1.up_prob != s2.up_prob


def test_score_compound_vs_signature_in_range(model):
    score = model.score_compound_vs_signature(
        ENZALUTAMIDE,
        up_genes=["AR", "KLK3"],
        down_genes=["PTEN", "NKX3-1"],
    )
    assert 0.0 <= score <= 1.0


def test_score_compound_vs_empty_signature(model):
    score = model.score_compound_vs_signature(ENZALUTAMIDE, up_genes=[], down_genes=[])
    assert score == 0.0


def test_predict_single_unknown_gene_does_not_crash(model):
    """Out-of-vocabulary genes should use hash fallback, not raise."""
    scores = model.predict_genes(ENZALUTAMIDE, ["TOTALLY_UNKNOWN_XYZ"])
    assert len(scores) == 1
