from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

import joblib
import numpy as np
from rdkit import Chem

from signalforge_ml.features import (
    _load_corr_cols,
    gene_symbol_to_vector,
    smiles_to_morgan,
)

# Default paths — relative to the ml/ package root
_PKG_ROOT = Path(__file__).parent.parent
_DEFAULT_MODEL = _PKG_ROOT / "artifacts" / "models" / "baseline.joblib"
_DEFAULT_MANIFEST = _PKG_ROOT / "artifacts" / "manifests" / "latest.json"

# Feature dimensions must match training config
_FP_RADIUS = 2
_FP_BITS = 2048
_NEUTRAL_MARGIN = 0.08


class GeneScore(NamedTuple):
    gene: str
    up_prob: float
    down_prob: float
    direction: str
    confidence: float


def load_manifest(path: str | Path = _DEFAULT_MANIFEST) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_smiles(smiles: str) -> str:
    """Return canonical SMILES or raise ValueError for invalid structures."""
    cleaned = (smiles or "").strip()
    if not cleaned:
        raise ValueError("SMILES string is empty.")
    molecule = Chem.MolFromSmiles(cleaned)
    if molecule is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")
    canonical = Chem.MolToSmiles(molecule)
    if not canonical:
        raise ValueError(f"Invalid SMILES string: {smiles}")
    return canonical


def _proba_to_score(gene: str, down_p: float, up_p: float) -> GeneScore:
    margin = abs(up_p - down_p)
    if margin < _NEUTRAL_MARGIN:
        direction = "neutral"
    elif up_p > down_p:
        direction = "up"
    else:
        direction = "down"
    return GeneScore(
        gene=gene,
        up_prob=round(up_p, 4),
        down_prob=round(down_p, 4),
        direction=direction,
        confidence=round(max(up_p, down_p), 4),
    )


def score_reversal_from_gene_map(
    gene_map: dict[str, GeneScore],
    up_genes: list[str],
    down_genes: list[str],
) -> float:
    hits = 0
    total = len(up_genes) + len(down_genes)
    if total == 0:
        return 0.0
    for g in up_genes:
        s = gene_map.get(g)
        if s and s.direction in ("down", "neutral"):
            hits += 1
    for g in down_genes:
        s = gene_map.get(g)
        if s and s.direction in ("up", "neutral"):
            hits += 1
    return round(hits / total, 4)


class SignalForgeModel:
    """Thin wrapper around the trained joblib model for online inference."""

    def __init__(
        self,
        model_path: str | Path = _DEFAULT_MODEL,
        fp_radius: int = _FP_RADIUS,
        fp_bits: int = _FP_BITS,
    ) -> None:
        self._model = joblib.load(model_path)
        self._fp_radius = fp_radius
        self._fp_bits = fp_bits
        self._expected_feature_count = getattr(self._model, "n_features_in_", None)
        corr_idx = _load_corr_cols()
        self._corr_idx = corr_idx if corr_idx is not None and len(corr_idx) > 0 else None

    def compound_vector(self, smiles: str) -> np.ndarray:
        """Morgan vector with the same LNCAPcorr selection used at training time."""
        morgan_full = smiles_to_morgan(smiles, self._fp_radius, self._fp_bits)
        if self._corr_idx is not None:
            return morgan_full[self._corr_idx]
        return morgan_full

    def predict_genes(
        self,
        smiles: str,
        genes: list[str],
        *,
        compound_vec: np.ndarray | None = None,
    ) -> list[GeneScore]:
        """Return per-gene regulation probabilities for a SMILES compound."""
        if not genes:
            return []
        morgan = compound_vec if compound_vec is not None else self.compound_vector(smiles)
        features = np.stack(
            [np.concatenate([morgan, gene_symbol_to_vector(gene)], axis=0) for gene in genes],
            axis=0,
        )
        if self._expected_feature_count is not None and features.shape[1] != self._expected_feature_count:
            raise ValueError(
                "Inference feature width mismatch: "
                f"built {features.shape[1]} features, "
                f"model expects {self._expected_feature_count}. "
                "Check that inference uses the same Morgan bit selection and gene encoder as training."
            )
        probas = self._model.predict_proba(features)
        return [
            _proba_to_score(gene, float(proba[0]), float(proba[1]))
            for gene, proba in zip(genes, probas, strict=True)
        ]

    def score_compounds_vs_signature(
        self,
        compound_vecs: list[np.ndarray],
        up_genes: list[str],
        down_genes: list[str],
    ) -> list[float]:
        """Batch-score many precomputed compound vectors against one signature."""
        all_genes = list(dict.fromkeys(up_genes + down_genes))
        if not compound_vecs or not all_genes:
            return [0.0] * len(compound_vecs)

        gene_vectors = np.stack([gene_symbol_to_vector(gene) for gene in all_genes], axis=0)
        n_compounds = len(compound_vecs)
        n_genes = len(all_genes)
        feature_width = compound_vecs[0].shape[0] + gene_vectors.shape[1]
        features = np.empty((n_compounds * n_genes, feature_width), dtype=np.float32)
        for i, compound_vec in enumerate(compound_vecs):
            start = i * n_genes
            end = start + n_genes
            features[start:end, : compound_vec.shape[0]] = compound_vec
            features[start:end, compound_vec.shape[0] :] = gene_vectors

        if self._expected_feature_count is not None and features.shape[1] != self._expected_feature_count:
            raise ValueError(
                "Inference feature width mismatch: "
                f"built {features.shape[1]} features, "
                f"model expects {self._expected_feature_count}."
            )

        probas = self._model.predict_proba(features)
        scores: list[float] = []
        for i in range(n_compounds):
            chunk = probas[i * n_genes : (i + 1) * n_genes]
            gene_map = {
                gene: _proba_to_score(gene, float(proba[0]), float(proba[1]))
                for gene, proba in zip(all_genes, chunk, strict=True)
            }
            scores.append(score_reversal_from_gene_map(gene_map, up_genes, down_genes))
        return scores

    def score_compound_vs_signature(
        self,
        smiles: str,
        up_genes: list[str],
        down_genes: list[str],
        *,
        compound_vec: np.ndarray | None = None,
    ) -> float:
        """Return a [0,1] reversal score: how well does this compound flip
        the signature (suppress up-genes, restore down-genes)?"""
        all_genes = list(dict.fromkeys(up_genes + down_genes))
        gene_map = {
            s.gene: s
            for s in self.predict_genes(smiles, all_genes, compound_vec=compound_vec)
        }
        return score_reversal_from_gene_map(gene_map, up_genes, down_genes)
