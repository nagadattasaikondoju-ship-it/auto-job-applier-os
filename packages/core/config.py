from typing import Literal

from pydantic import Field, field_validator
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
    # Tried in order when the chosen model is overloaded or out of free quota (each model has its own quota)
    gemini_fallback_models: list[str] = Field(
        default_factory=lambda: ["gemini-3.5-flash-lite", "gemini-3-flash-preview"]
    )

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

    # Hosted previews only: accept "dev-token-<uid>" logins without Firebase. Anyone can sign in
    # as anyone, so never enable this for real users.
    allow_dev_login: bool = False

    # Observability
    sentry_dsn: str = ""
    extension_id: str = ""

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        """Hosts hand out postgres:// URLs; the app needs the asyncpg driver."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix) :]
        return v

    @field_validator("direct_database_url")
    @classmethod
    def _plain_driver(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return "postgresql://" + v[len("postgres://") :]
        return v.replace("postgresql+asyncpg://", "postgresql://", 1)

    @property
    def dev_login_enabled(self) -> bool:
        return self.app_env in ("development", "test") or self.allow_dev_login


settings = Settings()
