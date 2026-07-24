from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "ForgeMind AI API"
    environment: str = "development"
    database_url: str = f"sqlite:///{BASE_DIR / 'forgemind.db'}"
    cors_origins: str = "http://localhost:3000"
    storage_dir: str = str(BASE_DIR / "storage")
    predictive_model_path: str = str(BASE_DIR / "ml" / "models" / "predictive_maintenance.joblib")
    predictive_metadata_path: str = str(BASE_DIR / "ml" / "models" / "predictive_maintenance.metadata.json")
    metropt_model_path: str = str(BASE_DIR / "ml" / "models" / "metropt_air_compressor.joblib")
    metropt_metadata_path: str = str(BASE_DIR / "ml" / "models" / "metropt_air_compressor.metadata.json")
    quality_model_path: str = str(BASE_DIR / "ml" / "models" / "quality_inspector.joblib")
    quality_metadata_path: str = str(BASE_DIR / "ml" / "models" / "quality_inspector.metadata.json")
    secret_key: str = "change-this-local-secret-before-deployment"
    token_hours: int = 12
    device_api_key: str = "forgemind-local-device-key"
    local_recovery_key: str = "ForgeMind-Recovery-2026"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    max_upload_mb: int = 12
    allow_local_registration: bool = True
    seed_default_users: bool = True

    cookie_secure: bool = False
    trust_proxy_headers: bool = False
    rate_limit_backend: str = "memory"
    redis_url: str | None = None
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "forgemind-private"

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() in {"production", "prod"}:
            unsafe = {
                "secret_key": "change-this-local-secret-before-deployment",
                "device_api_key": "forgemind-local-device-key",
                "local_recovery_key": "ForgeMind-Recovery-2026",
            }
            problems = [name for name, default in unsafe.items() if getattr(self, name) == default]
            if problems:
                raise ValueError("Unsafe production defaults: " + ", ".join(problems))
            if self.seed_default_users:
                raise ValueError("SEED_DEFAULT_USERS must be false in production")
            if self.allow_local_registration:
                raise ValueError("ALLOW_LOCAL_REGISTRATION must be false in production unless explicitly reviewed")
        return self

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
