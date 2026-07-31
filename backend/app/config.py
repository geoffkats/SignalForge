from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory — two levels up from this file (backend/app/config.py)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
# ml/ directory sits next to backend/
_ML_ARTIFACTS = _BACKEND_DIR.parent / "ml" / "artifacts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_prefix="SIGNALFORGE_",
        extra="ignore",
    )

    app_name: str = "SignalForge API"
    environment: str = "development"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    api_keys: list[str] = Field(default_factory=list)
    requests_per_minute: int = 60
    max_genes_per_request: int = 64
    max_signature_genes: int = 256
    model_version: str = "baseline-rf-v1"
    model_manifest_path: str = str(_ML_ARTIFACTS / "manifests" / "latest.json")
    model_artifact_path: str = str(_ML_ARTIFACTS / "models" / "baseline.joblib")
    compound_atlas_path: str = str(_ML_ARTIFACTS / "libraries" / "compound_atlas.json")


@lru_cache
def get_settings() -> Settings:
    return Settings()
