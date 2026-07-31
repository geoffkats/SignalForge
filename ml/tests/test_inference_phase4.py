"""Tests for compound atlas builder and optional deep inference loader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from signalforge_ml.build_atlas import build_compound_atlas
from signalforge_ml.inference import validate_smiles


def test_validate_smiles_canonicalizes():
    assert validate_smiles("CCO") == "CCO"


def test_validate_smiles_rejects_invalid():
    with pytest.raises(ValueError):
        validate_smiles("not-a-smiles%%%")


def test_build_compound_atlas_from_fixture(tmp_path: Path):
    csv_path = tmp_path / "smiles.csv"
    csv_path.write_text(
        "pert_id,canonical_smiles,pert_iname\n"
        "BRD-A1,CCO,ethanol\n"
        "BRD-A2,CCN,ethylamine\n"
        "BRD-A3,CCC,propane\n"
        "BRD-X1,CCO,duplicate-ethanol\n"
        "BRD-BAD,%%%bad%%%,badmol\n",
        encoding="utf-8",
    )
    out = tmp_path / "atlas.json"
    atlas = build_compound_atlas(smiles_csv=csv_path, out_path=out, target_size=10)
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["n_compounds"] == len(atlas)
    # Clinical panel (6) + unique valid named LINCS rows
    assert len(atlas) >= 6
    ids = {row["compound_id"] for row in atlas}
    assert "BRD-FBDF768A" in ids  # Enzalutamide clinical panel
    assert "BRD-A1" in ids
    assert "BRD-BAD" not in ids


def test_deep_loader_smoke_if_artifact_present():
    artifact = Path(__file__).resolve().parents[1] / "artifacts" / "models" / "deep_dual_encoder_smoke.pt"
    if not artifact.exists():
        pytest.skip("deep smoke artifact not present")
    pytest.importorskip("torch")
    from signalforge_ml.inference_deep import SignalForgeDeepModel

    model = SignalForgeDeepModel(artifact)
    scores = model.predict_genes("CCO", ["AR"])
    assert len(scores) == 1
    assert scores[0].direction in ("up", "down", "neutral")
    assert 0.0 <= scores[0].up_prob <= 1.0
