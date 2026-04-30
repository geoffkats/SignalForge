from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SIGNALFORGE_", extra="ignore")

    app_name: str = "SignalForge API"
    environment: str = "development"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    api_keys: list[str] = Field(default_factory=list)
    requests_per_minute: int = 60
    max_genes_per_request: int = 64
    max_signature_genes: int = 256
    model_version: str = "baseline-logreg-v1"
    model_manifest_path: str = "../ml/artifacts/manifests/latest.json"
    model_artifact_path: str = "../ml/artifacts/models/baseline.joblib"


@lru_cache
def get_settings() -> Settings:
    return Settings()