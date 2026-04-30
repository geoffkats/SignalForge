from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models import GeneEffectPrediction, RankedCompound

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compounds available for reverse-signature search
# Source: DeepCOP LNCaP androgen-receptor drug panel + clinical comparators
# ---------------------------------------------------------------------------
_REVERSE_COMPOUNDS = [
    ("BRD-FBDF768A",  "Enzalutamide",  "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F"),
    ("BRD-A80177499", "Bicalutamide",  "CC(CS(=O)(=O)c1ccc(F)cc1)(C#N)NC(=O)c1ccc(cc1)OC(F)(F)F"),
    ("BRD-K88742100", "Apalutamide",   "Cc1c(F)cccc1N1CC(C)(C)CN(c2ncc(C#N)c(=O)n2)C1=O"),
    ("BRD-K88742101", "Darolutamide",  "CC(O)c1cc(NC(=O)c2cc(C(F)(F)F)ccc2N)ccc1F"),
    ("BRD-K12345678", "Vorinostat",    "O=C(CCCCCCC(=O)Nc1ccccc1)NO"),
    ("BRD-K87654321", "Entinostat",    "CCOc1cc(NC(=O)Cc2ccc(NC(=O)c3ccncc3)cc2)ccc1N"),
]


@dataclass(slots=True)
class PredictorManifest:
    model_version: str
    compound_encoder: str
    gene_encoder: str
    training_status: str
    training_metrics: dict[str, float]
    metrics_source: str | None


def _extract_key_metrics(raw_metrics: Any) -> dict[str, float]:
    if not isinstance(raw_metrics, dict):
        return {}
    metrics: dict[str, float] = {}
    accuracy = raw_metrics.get("accuracy")
    if isinstance(accuracy, (int, float)):
        metrics["accuracy"] = round(float(accuracy), 6)
    macro_avg = raw_metrics.get("macro avg")
    if isinstance(macro_avg, dict):
        macro_f1 = macro_avg.get("f1-score")
        if isinstance(macro_f1, (int, float)):
            metrics["macro_f1"] = round(float(macro_f1), 6)
    weighted_avg = raw_metrics.get("weighted avg")
    if isinstance(weighted_avg, dict):
        weighted_f1 = weighted_avg.get("f1-score")
        if isinstance(weighted_f1, (int, float)):
            metrics["weighted_f1"] = round(float(weighted_f1), 6)
    return metrics


def _load_manifest(model_version: str, manifest_path: str | None) -> PredictorManifest:
    fallback = PredictorManifest(
        model_version=model_version,
        compound_encoder="morgan-2048",
        gene_encoder="go-fingerprint-1107",
        training_status="unknown",
        training_metrics={},
        metrics_source=None,
    )
    if not manifest_path:
        return fallback
    path = Path(manifest_path)
    if not path.exists():
        return fallback
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    algorithm = payload.get("algorithm", "Morgan-2048 + GO-fingerprint + LogisticRegression")
    status = payload.get("status", "unknown")
    resolved_version = payload.get("model_version", model_version)
    return PredictorManifest(
        model_version=resolved_version if isinstance(resolved_version, str) else model_version,
        compound_encoder=algorithm if isinstance(algorithm, str) else "morgan-2048",
        gene_encoder="go-fingerprint-1107",
        training_status=status if isinstance(status, str) else "unknown",
        training_metrics=_extract_key_metrics(payload.get("metrics")),
        metrics_source=str(path),
    )


# ---------------------------------------------------------------------------
# Lazy model loader — graceful fallback if signalforge_ml not on PYTHONPATH
# ---------------------------------------------------------------------------
_model_instance = None
_model_load_attempted = False


def _get_model(model_path: str):
    global _model_instance, _model_load_attempted
    if _model_load_attempted:
        return _model_instance
    _model_load_attempted = True
    try:
        from signalforge_ml.inference import SignalForgeModel  # noqa: PLC0415
        _model_instance = SignalForgeModel(model_path=model_path)
        logger.info("ML model loaded: %s", model_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ML model unavailable (%s) — heuristic active", exc)
        _model_instance = None
    return _model_instance


class SignalForgePredictor:
    def __init__(
        self,
        model_version: str,
        manifest_path: str | None = None,
        model_artifact_path: str | None = None,
    ) -> None:
        self.manifest = _load_manifest(model_version=model_version, manifest_path=manifest_path)
        self._artifact_path = model_artifact_path or "../ml/artifacts/models/baseline.joblib"

    # ------------------------------------------------------------------
    def predict_gene_effects(self, smiles: str, genes: list[str]) -> list[GeneEffectPrediction]:
        model = _get_model(self._artifact_path)
        if model is not None:
            return self._model_predict(model, smiles, genes)
        return self._heuristic_predict(smiles, genes)

    def _model_predict(self, model: Any, smiles: str, genes: list[str]) -> list[GeneEffectPrediction]:
        scores = model.predict_genes(smiles, genes)
        return [
            GeneEffectPrediction(
                gene=s.gene,
                direction=s.direction,
                up_probability=s.up_prob,
                down_probability=s.down_prob,
                confidence=s.confidence,
                rationale=(
                    f"LogisticRegression trained on LNCaP DESeq2 data (DeepCOP). "
                    f"Chemical features: Morgan-2048 (r=2). "
                    f"Gene features: LINCS L1000 GO-term fingerprint (978 landmark genes x 1107 GO terms). "
                    f"Model: {self.manifest.model_version}."
                ),
            )
            for s in scores
        ]

    def _heuristic_predict(self, smiles: str, genes: list[str]) -> list[GeneEffectPrediction]:
        import hashlib  # noqa: PLC0415
        predictions: list[GeneEffectPrediction] = []
        for gene in genes:
            digest = hashlib.sha256(f"{smiles}|{gene}".encode()).hexdigest()
            up_p = int(digest[:4], 16) / 65535
            down_p = int(digest[4:8], 16) / 65535
            total = up_p + down_p
            up_p /= total
            down_p /= total
            margin = abs(up_p - down_p)
            direction = "neutral" if margin < 0.08 else ("up" if up_p > down_p else "down")
            predictions.append(
                GeneEffectPrediction(
                    gene=gene, direction=direction,
                    up_probability=round(up_p, 4), down_probability=round(down_p, 4),
                    confidence=round(max(up_p, down_p), 4),
                    rationale="[Heuristic fallback] ML model unavailable. Score from compound+gene hash.",
                )
            )
        return predictions

    # ------------------------------------------------------------------
    def reverse_signature_search(
        self, up_genes: list[str], down_genes: list[str], top_k: int
    ) -> list[RankedCompound]:
        model = _get_model(self._artifact_path)
        ranked: list[RankedCompound] = []
        for compound_id, compound_name, smiles in _REVERSE_COMPOUNDS:
            if model is not None:
                score = model.score_compound_vs_signature(smiles, up_genes, down_genes)
                explanation = (
                    f"Reversal score: fraction of signature genes whose predicted "
                    f"direction opposes the query. Model: {self.manifest.model_version}."
                )
            else:
                import hashlib  # noqa: PLC0415
                sig = "|".join(sorted(up_genes)) + "::" + "|".join(sorted(down_genes))
                digest = hashlib.sha256(f"{compound_id}|{sig}".encode()).hexdigest()
                score = round(int(digest[:6], 16) / 16777215, 4)
                explanation = "[Heuristic fallback] Score from compound+signature hash."
            ranked.append(
                RankedCompound(
                    compound_id=compound_id,
                    compound_name=compound_name,
                    smiles=smiles,
                    reversal_score=score,
                    explanation=explanation,
                )
            )
        ranked.sort(key=lambda r: r.reversal_score, reverse=True)
        return ranked[:top_k]