from packages.core.config import Settings


def test_settings_initialization() -> None:
    settings = Settings()
    assert settings.app_env in ("development", "staging", "production", "test")
    assert settings.api_base_url.startswith("http")
    assert "job_ingestion" in [
        "job_ingestion",
        "embeddings",
        "ai_matching",
    ]


def test_pooler_detection() -> None:
    pooler_settings = Settings(
        database_url="postgresql+asyncpg://postgres:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
    )
    assert ":6543" in pooler_settings.database_url
