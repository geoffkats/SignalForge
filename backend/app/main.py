from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.security import InMemoryRateLimitMiddleware, RequestContextMiddleware, SecurityHeadersMiddleware
from app.services.predictor import SignalForgePredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.predictor = SignalForgePredictor(
        model_version=settings.model_version,
        manifest_path=settings.model_manifest_path,
        model_artifact_path=settings.model_artifact_path,
        compound_atlas_path=settings.compound_atlas_path,
        eager_load=True,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        summary="Premium biotech API for compound-to-gene effect analysis and reverse-signature search.",
        description=(
            "SignalForge exposes a research-grade interface for molecule-to-transcriptome exploration.\n\n"
            "The API supports health checks, platform metadata, gene-effect prediction, and reverse-signature search. "
            "All prediction flows are wrapped with request tracing, rate limiting, and research-use-only policy guardrails.\n\n"
            "Use the Swagger UI to inspect request examples, response schemas, and live try-it-out behavior."
        ),
        version="0.1.0",
        contact={"name": "SignalForge Maintainers"},
        license_info={"name": "AGPL-3.0-or-later", "identifier": "AGPL-3.0-or-later"},
        openapi_tags=[
            {"name": "Operations", "description": "Runtime health and operational readiness endpoints."},
            {"name": "Platform", "description": "Static metadata used to describe the active SignalForge instance."},
            {
                "name": "Inference",
                "description": "Core biotech inference endpoints for gene-effect prediction and reverse-signature search.",
            },
        ],
        swagger_ui_parameters={
            "displayRequestDuration": True,
            "docExpansion": "list",
            "filter": True,
            "tryItOutEnabled": True,
            "defaultModelsExpandDepth": 2,
        },
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(InMemoryRateLimitMiddleware, requests_per_minute=settings.requests_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    app.include_router(router)
    return app


app = create_app()