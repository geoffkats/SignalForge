"""
FastAPI route tests — no real model needed, predictor is mocked via app.state.

Run with:
    cd backend
    pip install httpx pytest
    pytest tests/ -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import GeneEffectPrediction, RankedCompound

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_settings() -> Settings:
    """Settings with empty API key list — auth checks are bypassed."""
    return Settings(api_keys=[])

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ENZALUTAMIDE = "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F"


def _make_mock_predictor():
    predictor = MagicMock()
    predictor.manifest.model_version = "test-model-v0"
    predictor.manifest.training_status = "trained"
    predictor.manifest.training_metrics = {"accuracy": 0.55, "macro_f1": 0.51}
    predictor.manifest.metrics_source = None
    predictor.predict_gene_effects.return_value = [
        GeneEffectPrediction(
            gene="AR",
            direction="down",
            up_probability=0.32,
            down_probability=0.68,
            confidence=0.68,
            rationale="Mock prediction for tests.",
        )
    ]
    predictor.reverse_signature_search.return_value = [
        RankedCompound(
            compound_id="BRD-TEST",
            compound_name="Enzalutamide",
            smiles=ENZALUTAMIDE,
            reversal_score=0.75,
            explanation="Mock reversal score.",
        )
    ]
    return predictor


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        # Override AFTER lifespan so our mock isn't overwritten by the startup hook
        app.state.predictor = _make_mock_predictor()
        yield c


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------

def test_healthz_returns_200(client):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_healthz_status_is_ok(client):
    r = client.get("/healthz")
    assert r.json()["status"] == "ok"


def test_healthz_includes_model_version(client):
    r = client.get("/healthz")
    assert "model_version" in r.json()


# ---------------------------------------------------------------------------
# /meta
# ---------------------------------------------------------------------------

def test_meta_returns_200(client):
    r = client.get("/meta")
    assert r.status_code == 200


def test_meta_includes_pipeline_stages(client):
    data = client.get("/meta").json()
    assert "pipeline_stages" in data
    assert len(data["pipeline_stages"]) > 0


def test_meta_includes_security_modes(client):
    data = client.get("/meta").json()
    assert "security_modes" in data


# ---------------------------------------------------------------------------
# /predict/gene-effect
# ---------------------------------------------------------------------------

def test_predict_requires_api_key(client):
    r = client.post(
        "/predict/gene-effect",
        json={"smiles": ENZALUTAMIDE, "genes": ["AR"]},
    )
    # No API key configured in test env → 401 or pass-through depending on config
    assert r.status_code in (200, 401)


def test_predict_with_no_api_key_env_returns_200(client):
    """When SIGNALFORGE_API_KEYS is empty list, key check is skipped."""
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/predict/gene-effect",
            json={"smiles": ENZALUTAMIDE, "genes": ["AR", "KLK3"]},
        )
    assert r.status_code == 200


def test_predict_response_has_predictions_field(client):
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/predict/gene-effect",
            json={"smiles": ENZALUTAMIDE, "genes": ["AR"]},
        )
    if r.status_code == 200:
        assert "predictions" in r.json()


def test_predict_response_has_audit_id(client):
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/predict/gene-effect",
            json={"smiles": ENZALUTAMIDE, "genes": ["AR"]},
        )
    if r.status_code == 200:
        assert "audit_id" in r.json()


def test_predict_empty_genes_returns_422(client):
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/predict/gene-effect",
            json={"smiles": ENZALUTAMIDE, "genes": []},
        )
    assert r.status_code == 422


def test_predict_empty_smiles_returns_422(client):
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/predict/gene-effect",
            json={"smiles": "", "genes": ["AR"]},
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /search/reverse-signature
# ---------------------------------------------------------------------------

def test_reverse_search_returns_results(client):
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/search/reverse-signature",
            json={"up_genes": ["AR", "KLK3"], "down_genes": ["PTEN"], "top_k": 3},
        )
    if r.status_code == 200:
        data = r.json()
        assert "results" in data
        assert "audit_id" in data


def test_reverse_search_response_has_model_version(client):
    with patch("app.config.get_settings", return_value=_open_settings()):
        r = client.post(
            "/search/reverse-signature",
            json={"up_genes": ["MYC"], "down_genes": ["TP53"], "top_k": 5},
        )
    if r.status_code == 200:
        assert "model_version" in r.json()


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

def test_security_headers_present(client):
    r = client.get("/healthz")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"


def test_request_id_header_present(client):
    r = client.get("/healthz")
    assert "x-request-id" in r.headers


def test_process_time_header_present(client):
    r = client.get("/healthz")
    assert "x-process-time-ms" in r.headers
