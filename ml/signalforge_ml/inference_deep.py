"""Optional PyTorch dual-encoder inference — import only when serving a .pt artifact."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from signalforge_ml.features import gene_symbol_to_vector, smiles_to_morgan
from signalforge_ml.inference import GeneScore, _proba_to_score, score_reversal_from_gene_map
from signalforge_ml.model import SignalForgeNet

_FP_RADIUS = 2
_FP_BITS = 2048


class SignalForgeDeepModel:
    """Online inference wrapper for SignalForgeNet dual-encoder checkpoints."""

    def __init__(self, model_path: str | Path) -> None:
        path = Path(model_path)
        bundle = torch.load(path, map_location="cpu", weights_only=False)
        if not isinstance(bundle, dict) or "state_dict" not in bundle:
            raise ValueError(f"Deep checkpoint missing state_dict: {path}")

        compound_dim = int(bundle.get("compound_dim", _FP_BITS))
        gene_dim = int(bundle.get("gene_dim", 1107))
        self._compound_dim = compound_dim
        self._gene_dim = gene_dim
        self._scaler_c = bundle.get("scaler_c")
        self._scaler_g = bundle.get("scaler_g")
        self._fp_radius = _FP_RADIUS
        self._fp_bits = compound_dim if compound_dim in (1024, 2048) else _FP_BITS

        self._model = SignalForgeNet(compound_dim=compound_dim, gene_dim=gene_dim)
        self._model.load_state_dict(bundle["state_dict"])
        self._model.eval()

    def compound_vector(self, smiles: str) -> np.ndarray:
        vec = smiles_to_morgan(smiles, self._fp_radius, self._fp_bits)
        if vec.shape[0] != self._compound_dim:
            raise ValueError(
                f"Compound vector width {vec.shape[0]} != model compound_dim {self._compound_dim}"
            )
        if self._scaler_c is not None:
            vec = self._scaler_c.transform(vec.reshape(1, -1)).astype(np.float32).ravel()
        return vec.astype(np.float32, copy=False)

    def _gene_vector(self, gene: str) -> np.ndarray:
        vec = gene_symbol_to_vector(gene, width=self._gene_dim)
        if self._scaler_g is not None:
            vec = self._scaler_g.transform(vec.reshape(1, -1)).astype(np.float32).ravel()
        return vec.astype(np.float32, copy=False)

    def predict_genes(
        self,
        smiles: str,
        genes: list[str],
        *,
        compound_vec: np.ndarray | None = None,
    ) -> list[GeneScore]:
        morgan = compound_vec if compound_vec is not None else self.compound_vector(smiles)
        c = torch.from_numpy(np.asarray(morgan, dtype=np.float32)).unsqueeze(0)
        scores: list[GeneScore] = []
        with torch.no_grad():
            for gene in genes:
                g = torch.from_numpy(self._gene_vector(gene)).unsqueeze(0)
                proba = self._model.predict_proba(c, g)[0].cpu().numpy()
                scores.append(_proba_to_score(gene, float(proba[0]), float(proba[1])))
        return scores

    def score_compound_vs_signature(
        self,
        smiles: str,
        up_genes: list[str],
        down_genes: list[str],
        *,
        compound_vec: np.ndarray | None = None,
    ) -> float:
        all_genes = list(dict.fromkeys(up_genes + down_genes))
        gene_map = {
            s.gene: s
            for s in self.predict_genes(smiles, all_genes, compound_vec=compound_vec)
        }
        return score_reversal_from_gene_map(gene_map, up_genes, down_genes)
