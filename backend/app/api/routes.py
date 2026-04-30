from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.config import get_settings
from app.models import (
    GeneEffectRequest,
    GeneEffectResponse,
    HealthResponse,
    MetaResponse,
    ReverseSignatureRequest,
    ReverseSignatureResponse,
)
from app.security import enforce_biotech_query_policy, require_api_key
from app.services.audit import build_audit_record

router = APIRouter()


@router.get(
    "/healthz",
    response_model=HealthResponse,
    tags=["Operations"],
    summary="Service health check",
    description="Returns the API health state, active model version, and environment label for runtime checks.",
)
def healthz(request: Request) -> HealthResponse:
    settings = get_settings()
    predictor = request.app.state.predictor

    return HealthResponse(
        status="ok",
        model_version=predictor.manifest.model_version,
        environment=settings.environment,
    )


@router.get(
    "/meta",
    response_model=MetaResponse,
    tags=["Platform"],
    summary="Platform metadata",
    description=(
        "Returns platform level metadata used by the frontend, including model version, training status, "
        "training metrics, enabled security modes, and pipeline stages."
    ),
)
def meta(request: Request) -> MetaResponse:
    settings = get_settings()
    predictor = request.app.state.predictor
    return MetaResponse(
        app_name=settings.app_name,
        model_version=predictor.manifest.model_version,
        training_status=predictor.manifest.training_status,
        training_metrics=predictor.manifest.training_metrics,
        metrics_source=predictor.manifest.metrics_source,
        security_modes=["api-key", "rate-limit", "request-id", "research-use-only"],
        pipeline_stages=["ingestion", "feature-store", "training", "inference", "audit"],
    )


@router.post(
    "/predict/gene-effect",
    response_model=GeneEffectResponse,
    dependencies=[Depends(require_api_key)],
    tags=["Inference"],
    summary="Predict gene regulation effects",
    description=(
        "Scores a compound against a supplied gene panel and returns predicted up, down, or neutral regulation with"
        " confidence values and an audit identifier."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Gene level regulation predictions were generated successfully."},
        401: {"description": "Missing or invalid API key."},
        422: {"description": "The submitted gene panel exceeded policy limits or failed validation."},
        429: {"description": "Rate limit exceeded for the current client and API key combination."},
    },
)
def predict_gene_effect(request: Request, payload: GeneEffectRequest) -> GeneEffectResponse:
    predictor = request.app.state.predictor
    enforce_biotech_query_policy(request, gene_count=len(payload.genes))
    predictions = predictor.predict_gene_effects(payload.smiles, payload.genes)
    audit = build_audit_record(request.state.request_id, "predict.gene_effect", request.state.query_classification)
    return GeneEffectResponse(
        model_version=predictor.manifest.model_version,
        predictions=predictions,
        audit_id=audit.audit_id,
    )


@router.post(
    "/search/reverse-signature",
    response_model=ReverseSignatureResponse,
    dependencies=[Depends(require_api_key)],
    tags=["Inference"],
    summary="Search reversal candidates",
    description=(
        "Accepts a desired disease or pathway signature and ranks candidate compounds that may reverse that expression"
        " pattern within the current SignalForge model."
    ),
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Candidate compounds were ranked successfully."},
        401: {"description": "Missing or invalid API key."},
        422: {"description": "The submitted signature exceeded policy limits or failed validation."},
        429: {"description": "Rate limit exceeded for the current client and API key combination."},
    },
)
def reverse_signature(request: Request, payload: ReverseSignatureRequest) -> ReverseSignatureResponse:
    predictor = request.app.state.predictor
    signature_count = len(payload.up_genes) + len(payload.down_genes)
    enforce_biotech_query_policy(request, gene_count=0, signature_count=signature_count)
    results = predictor.reverse_signature_search(payload.up_genes, payload.down_genes, payload.top_k)
    audit = build_audit_record(request.state.request_id, "search.reverse_signature", request.state.query_classification)
    return ReverseSignatureResponse(
        model_version=predictor.manifest.model_version,
        results=results,
        audit_id=audit.audit_id,
    )