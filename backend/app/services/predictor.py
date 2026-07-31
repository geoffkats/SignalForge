from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models import GeneEffectPrediction, RankedCompound

logger = logging.getLogger(__name__)

_FALLBACK_ATLAS: list[dict[str, str]] = [
    {
        "compound_id": "BRD-FBDF768A",
        "compound_name": "Enzalutamide",
        "smiles": "CC1(C)C(=O)N(c2ccc(C#N)cc2C(F)(F)F)C(=S)N1c3ccc(C(=O)NC)cc3F",
    },
    {
        "compound_id": "BRD-A80177499",
        "compound_name": "Bicalutamide",
        "smiles": "CC(CS(=O)(=O)c1ccc(F)cc1)(C#N)NC(=O)c1ccc(cc1)OC(F)(F)F",
    },
    {
        "compound_id": "BRD-K88742100",
        "compound_name": "Apalutamide",
        "smiles": "Cc1c(F)cccc1N1CC(C)(C)CN(c2ncc(C#N)c(=O)n2)C1=O",
    },
    {
        "compound_id": "BRD-K88742101",
        "compound_name": "Darolutamide",
        "smiles": "CC(O)c1cc(NC(=O)c2cc(C(F)(F)F)ccc2N)ccc1F",
    },
    {
        "compound_id": "BRD-K12345678",
        "compound_name": "Vorinostat",
        "smiles": "O=C(CCCCCCC(=O)Nc1ccccc1)NO",
    },
    {
        "compound_id": "BRD-K87654321",
        "compound_name": "Entinostat",
        "smiles": "CCOc1cc(NC(=O)Cc2ccc(NC(=O)c3ccncc3)cc2)ccc1N",
    },
]


@dataclass(slots=True)
class PredictorManifest:
    model_version: str
    algorithm: str
    compound_encoder: str
    gene_encoder: str
    training_status: str
    training_metrics: dict[str, float]
    metrics_source: str | None


@dataclass(slots=True)
class AtlasCompound:
    compound_id: str
    compound_name: str
    smiles: str
    feature_vector: Any | None = None


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
    # Flat keys used by some manifests
    for key in ("macro_f1", "weighted_f1", "roc_auc", "rauc"):
        value = raw_metrics.get(key)
        if isinstance(value, (int, float)) and key not in metrics:
            metrics[key] = round(float(value), 6)
    return metrics


def _load_manifest(model_version: str, manifest_path: str | None) -> PredictorManifest:
    fallback = PredictorManifest(
        model_version=model_version,
        algorithm="Morgan-2048 + GO-fingerprint + RandomForest",
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
    algorithm = payload.get("algorithm", fallback.algorithm)
    status = payload.get("status", "unknown")
    resolved_version = payload.get("model_version", model_version)
    return PredictorManifest(
        model_version=resolved_version if isinstance(resolved_version, str) else model_version,
        algorithm=algorithm if isinstance(algorithm, str) else fallback.algorithm,
        compound_encoder="morgan-2048",
        gene_encoder="go-fingerprint-1107",
        training_status=status if isinstance(status, str) else "unknown",
        training_metrics=_extract_key_metrics(payload.get("metrics") or payload),
        metrics_source=str(path),
    )


def _load_atlas(atlas_path: str | None) -> list[AtlasCompound]:
    rows: list[dict[str, str]] = _FALLBACK_ATLAS
    if atlas_path:
        path = Path(atlas_path)
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                compounds = payload.get("compounds", payload if isinstance(payload, list) else [])
                if isinstance(compounds, list) and compounds:
                    rows = [
                        {
                            "compound_id": str(c["compound_id"]),
                            "compound_name": str(c["compound_name"]),
                            "smiles": str(c["smiles"]),
                        }
                        for c in compounds
                        if isinstance(c, dict) and {"compound_id", "compound_name", "smiles"} <= set(c)
                    ]
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning("Failed to load compound atlas (%s) — using clinical fallback", exc)
        else:
            logger.warning("Compound atlas missing at %s — using clinical fallback", atlas_path)

    return [
        AtlasCompound(
            compound_id=row["compound_id"],
            compound_name=row["compound_name"],
            smiles=row["smiles"],
        )
        for row in rows
    ]


def _load_inference_model(model_path: str) -> Any | None:
    path = Path(model_path)
    if not path.exists():
        logger.warning("Model artifact missing: %s", model_path)
        return None
    try:
        if path.suffix.lower() == ".pt":
            from signalforge_ml.inference_deep import SignalForgeDeepModel  # noqa: PLC0415

            model = SignalForgeDeepModel(model_path=path)
        else:
            from signalforge_ml.inference import SignalForgeModel  # noqa: PLC0415

            model = SignalForgeModel(model_path=path)
        logger.info("ML model loaded: %s", model_path)
        return model
    except Exception as exc:  # noqa: BLE001
        logger.warning("ML model unavailable (%s) — heuristic active", exc)
        return None


class SignalForgePredictor:
    def __init__(
        self,
        model_version: str,
        manifest_path: str | None = None,
        model_artifact_path: str | None = None,
        compound_atlas_path: str | None = None,
        *,
        eager_load: bool = True,
    ) -> None:
        self.manifest = _load_manifest(model_version=model_version, manifest_path=manifest_path)
        self._artifact_path = model_artifact_path or "../ml/artifacts/models/baseline.joblib"
        self._atlas = _load_atlas(compound_atlas_path)
        self._model: Any | None = None
        self.inference_mode: str = "heuristic"
        if eager_load:
            self.load_model()

    @property
    def atlas_size(self) -> int:
        return len(self._atlas)

    def load_model(self) -> None:
        self._model = _load_inference_model(self._artifact_path)
        self.inference_mode = "model" if self._model is not None else "heuristic"
        if self._model is not None and hasattr(self._model, "compound_vector"):
            for entry in self._atlas:
                try:
                    entry.feature_vector = self._model.compound_vector(entry.smiles)
                except Exception:  # noqa: BLE001
                    entry.feature_vector = None

    def _rationale(self) -> str:
        return (
            f"{self.manifest.algorithm}. "
            f"Compound encoder: {self.manifest.compound_encoder}. "
            f"Gene encoder: {self.manifest.gene_encoder}. "
            f"Model: {self.manifest.model_version}."
        )

    def validate_smiles(self, smiles: str) -> str:
        try:
            from signalforge_ml.inference import validate_smiles as _validate  # noqa: PLC0415

            return _validate(smiles)
        except ImportError:
            cleaned = (smiles or "").strip()
            if not cleaned:
                raise ValueError("SMILES string is empty.") from None
            return cleaned

    def predict_gene_effects(self, smiles: str, genes: list[str]) -> list[GeneEffectPrediction]:
        canonical = self.validate_smiles(smiles)
        if self._model is not None:
            return self._model_predict(self._model, canonical, genes)
        return self._heuristic_predict(canonical, genes)

    def _model_predict(self, model: Any, smiles: str, genes: list[str]) -> list[GeneEffectPrediction]:
        scores = model.predict_genes(smiles, genes)
        rationale = self._rationale()
        return [
            GeneEffectPrediction(
                gene=s.gene,
                direction=s.direction,
                up_probability=s.up_prob,
                down_probability=s.down_prob,
                confidence=s.confidence,
                rationale=rationale,
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
                    gene=gene,
                    direction=direction,
                    up_probability=round(up_p, 4),
                    down_probability=round(down_p, 4),
                    confidence=round(max(up_p, down_p), 4),
                    rationale="[Heuristic fallback] ML model unavailable. Score from compound+gene hash.",
                )
            )
        return predictions

    def reverse_signature_search(
        self, up_genes: list[str], down_genes: list[str], top_k: int
    ) -> list[RankedCompound]:
        explanation_model = (
            f"Reversal score: fraction of signature genes whose predicted "
            f"direction opposes the query. Model: {self.manifest.model_version}."
        )

        # Fast path: one batched RF call across the whole atlas.
        if self._model is not None and hasattr(self._model, "score_compounds_vs_signature"):
            ready = [entry for entry in self._atlas if entry.feature_vector is not None]
            if ready:
                scores = self._model.score_compounds_vs_signature(
                    [entry.feature_vector for entry in ready],
                    up_genes,
                    down_genes,
                )
                ranked = [
                    RankedCompound(
                        compound_id=entry.compound_id,
                        compound_name=entry.compound_name,
                        smiles=entry.smiles,
                        reversal_score=score,
                        explanation=explanation_model,
                    )
                    for entry, score in zip(ready, scores, strict=True)
                ]
                ranked.sort(key=lambda r: r.reversal_score, reverse=True)
                return ranked[:top_k]

        ranked: list[RankedCompound] = []
        for entry in self._atlas:
            if self._model is not None:
                try:
                    score = self._model.score_compound_vs_signature(
                        entry.smiles,
                        up_genes,
                        down_genes,
                        compound_vec=entry.feature_vector,
                    )
                except TypeError:
                    try:
                        score = self._model.score_compound_vs_signature(
                            entry.smiles, up_genes, down_genes
                        )
                    except ValueError:
                        continue
                except ValueError:
                    continue
                explanation = explanation_model
            else:
                import hashlib  # noqa: PLC0415

                sig = "|".join(sorted(up_genes)) + "::" + "|".join(sorted(down_genes))
                digest = hashlib.sha256(f"{entry.compound_id}|{sig}".encode()).hexdigest()
                score = round(int(digest[:6], 16) / 16777215, 4)
                explanation = "[Heuristic fallback] Score from compound+signature hash."
            ranked.append(
                RankedCompound(
                    compound_id=entry.compound_id,
                    compound_name=entry.compound_name,
                    smiles=entry.smiles,
                    reversal_score=score,
                    explanation=explanation,
                )
            )
        ranked.sort(key=lambda r: r.reversal_score, reverse=True)
        return ranked[:top_k]
