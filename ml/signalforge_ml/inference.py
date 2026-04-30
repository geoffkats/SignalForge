from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

import joblib
import numpy as np

from signalforge_ml.features import smiles_to_morgan, gene_symbol_to_vector

# Default paths — relative to the ml/ package root
_PKG_ROOT = Path(__file__).parent.parent
_DEFAULT_MODEL = _PKG_ROOT / "artifacts" / "models" / "baseline.joblib"
_DEFAULT_MANIFEST = _PKG_ROOT / "artifacts" / "manifests" / "latest.json"

# Feature dimensions must match training config
_FP_RADIUS = 2
_FP_BITS = 2048


class GeneScore(NamedTuple):
    gene: str
    up_prob: float
    down_prob: float
    direction: str
    confidence: float


def load_manifest(path: str | Path = _DEFAULT_MANIFEST) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict_genes(self, smiles: str, genes: list[str]) -> list[GeneScore]:
        """Return per-gene regulation probabilities for a SMILES compound."""
        morgan = smiles_to_morgan(smiles, self._fp_radius, self._fp_bits)
        scores: list[GeneScore] = []
        for gene in genes:
            go_vec = gene_symbol_to_vector(gene)
            feature = np.concatenate([morgan, go_vec], axis=0).reshape(1, -1)
            proba = self._model.predict_proba(feature)[0]
            # class order: 0=down, 1=up  (matches training label map)
            down_p = float(proba[0])
            up_p = float(proba[1])
            margin = abs(up_p - down_p)
            if margin < 0.08:
                direction = "neutral"
            elif up_p > down_p:
                direction = "up"
            else:
                direction = "down"
            scores.append(
                GeneScore(
                    gene=gene,
                    up_prob=round(up_p, 4),
                    down_prob=round(down_p, 4),
                    direction=direction,
                    confidence=round(max(up_p, down_p), 4),
                )
            )
        return scores

    def score_compound_vs_signature(
        self,
        smiles: str,
        up_genes: list[str],
        down_genes: list[str],
    ) -> float:
        """Return a [0,1] reversal score: how well does this compound flip
        the signature (suppress up-genes, restore down-genes)?"""
        all_genes = list(dict.fromkeys(up_genes + down_genes))
        gene_map = {s.gene: s for s in self.predict_genes(smiles, all_genes)}

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