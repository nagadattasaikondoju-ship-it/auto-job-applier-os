from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Environment
    app_env: Literal["development", "staging", "production", "test"] = "development"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://applyon:applyon_secret@localhost:5432/applyon"
    direct_database_url: str = "postgresql://applyon:applyon_secret@localhost:5432/applyon"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    is_supabase_pooler: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Firebase Auth & Storage
    firebase_project_id: str = "applyon-dev"
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    firebase_storage_bucket: str = ""

    # Supabase (Fallback)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model_lite: str = "gemini-3.1-flash-lite"
    gemini_model_fast: str = "gemini-3.5-flash"
    gemini_model_smart: str = "gemini-3.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"

    # Job Ingestion
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    crawler_user_agent: str = "ApplyonBot/1.0 (+https://applyon.in/bot)"

    # Transactional Email (Resend)
    resend_api_key: str = ""
    email_from: str = "onboarding@applyon.in"

    # Payments (Razorpay)
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Security
    field_encryption_key: str = "J9NkJw6P4v0sXU3Z7Bq1W8e5R2tY4u6I8o0pAaBbCc="
    jwt_secret_key: str = "applyon-local-dev-jwt-secret-replace-in-production"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
        ]
    )

    # Observability
    sentry_dsn: str = ""
    extension_id: str = ""


settings = Settings()
