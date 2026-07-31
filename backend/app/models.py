from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GeneEffectRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "smiles": "CC1=C(C(=CC=C1)C(F)(F)F)N2C(=O)SC(N(C2=O)C3CC3)=N",
                "genes": ["AR", "KLK3", "TMPRSS2", "FOXA1"],
                "context": "LNCaP androgen receptor program",
            }
        }
    )

    smiles: str = Field(
        min_length=1,
        max_length=512,
        description="SMILES representation of the query compound.",
        examples=["CC1=C(C(=CC=C1)C(F)(F)F)N2C(=O)SC(N(C2=O)C3CC3)=N"],
    )
    genes: list[str] = Field(
        min_length=1,
        max_length=64,
        description="Gene symbols to score for predicted up or down regulation.",
        examples=[["AR", "KLK3", "TMPRSS2", "FOXA1"]],
    )
    context: str | None = Field(
        default=None,
        max_length=128,
        description="Optional assay or biological context label used for audit traceability.",
        examples=["LNCaP androgen receptor program"],
    )

    @field_validator("genes")
    @classmethod
    def normalize_genes(cls, value: list[str]) -> list[str]:
        cleaned = [gene.strip().upper() for gene in value if gene.strip()]
        if not cleaned:
            raise ValueError("At least one gene is required.")
        return cleaned


class GeneEffectPrediction(BaseModel):
    gene: str = Field(description="Gene symbol returned from the request gene panel.")
    direction: Literal["up", "down", "neutral"] = Field(
        description="Predicted dominant regulation direction for the gene."
    )
    up_probability: float = Field(description="Estimated probability of up regulation.")
    down_probability: float = Field(description="Estimated probability of down regulation.")
    confidence: float = Field(description="Confidence score derived from the dominant direction probability.")
    rationale: str = Field(description="Human readable explanation for the current model output.")


class GeneEffectResponse(BaseModel):
    model_version: str = Field(description="Version of the model or heuristic backing the response.")
    inference_mode: Literal["model", "heuristic"] = Field(
        description="Whether the response used a loaded ML artifact or the deterministic heuristic fallback."
    )
    predictions: list[GeneEffectPrediction] = Field(description="Gene level prediction objects for the submitted panel.")
    audit_id: str = Field(description="Request scoped audit identifier for traceability.")


class ReverseSignatureRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "up_genes": ["MYC", "E2F1"],
                "down_genes": ["TP53", "CDKN1A"],
                "top_k": 5,
            }
        }
    )

    up_genes: list[str] = Field(
        default_factory=list,
        max_length=256,
        description="Genes to drive downward when searching for reversal candidates.",
        examples=[["MYC", "E2F1"]],
    )
    down_genes: list[str] = Field(
        default_factory=list,
        max_length=256,
        description="Genes to restore upward when searching for reversal candidates.",
        examples=[["TP53", "CDKN1A"]],
    )
    top_k: int = Field(default=10, ge=1, le=50, description="Maximum number of ranked compounds to return.")

    @field_validator("up_genes", "down_genes")
    @classmethod
    def normalize_signature(cls, value: list[str]) -> list[str]:
        return [gene.strip().upper() for gene in value if gene.strip()]


class RankedCompound(BaseModel):
    compound_id: str = Field(description="Stable identifier for the ranked compound.")
    compound_name: str = Field(description="Human readable compound label.")
    smiles: str = Field(description="SMILES representation for the ranked compound.")
    reversal_score: float = Field(description="Higher is better for reversal alignment in the current model.")
    explanation: str = Field(description="Human readable explanation of the ranking result.")


class ReverseSignatureResponse(BaseModel):
    model_version: str = Field(description="Version of the model or heuristic backing the ranking.")
    inference_mode: Literal["model", "heuristic"] = Field(
        description="Whether the ranking used a loaded ML artifact or the deterministic heuristic fallback."
    )
    results: list[RankedCompound] = Field(description="Ranked reversal candidates sorted by descending score.")
    audit_id: str = Field(description="Request scoped audit identifier for traceability.")


class HealthResponse(BaseModel):
    status: str = Field(description="Service health indicator.")
    model_version: str = Field(description="Version of the active predictor service.")
    inference_mode: Literal["model", "heuristic"] = Field(
        description="Whether the predictor loaded a real model artifact at startup."
    )
    atlas_size: int = Field(description="Number of compounds available for reverse-signature search.")
    environment: str = Field(description="Current backend environment label.")


class MetaResponse(BaseModel):
    app_name: str = Field(description="Public application name exposed by the backend.")
    model_version: str = Field(description="Version of the active predictor service.")
    inference_mode: Literal["model", "heuristic"] = Field(
        description="Whether the predictor loaded a real model artifact at startup."
    )
    atlas_size: int = Field(description="Number of compounds available for reverse-signature search.")
    training_status: str = Field(description="Training status for the currently loaded model manifest.")
    training_metrics: dict[str, float] = Field(
        description=(
            "Evaluation metrics surfaced from the latest training manifest for transparency. "
            "Common keys include accuracy, roc_auc or rauc, macro_f1, and weighted_f1."
        )
    )
    metrics_source: str | None = Field(default=None, description="Path of the manifest used to source metrics.")
    security_modes: list[str] = Field(description="Enabled request protection layers.")
    pipeline_stages: list[str] = Field(description="High level stages of the SignalForge workflow.")