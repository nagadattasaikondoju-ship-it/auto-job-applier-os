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


def test_neon_and_supabase_urls_work_with_asyncpg() -> None:
    from packages.core.config import Settings

    neon = "postgresql://u:p@ep-cool-name-123.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    s = Settings(database_url=neon, direct_database_url=neon)
    assert s.database_url == "postgresql+asyncpg://u:p@ep-cool-name-123.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
    assert s.direct_database_url == "postgresql://u:p@ep-cool-name-123.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
    plain = Settings(database_url="postgres://u:p@host:5432/db").database_url
    assert plain == "postgresql+asyncpg://u:p@host:5432/db"
    only_cb = Settings(database_url="postgresql://u:p@h/db?channel_binding=require").database_url
    assert only_cb == "postgresql+asyncpg://u:p@h/db"
