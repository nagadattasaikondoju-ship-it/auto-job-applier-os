from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from packages.core.config import settings

# Determine if connecting to a transaction pooler (e.g. Supabase port 6543 or explicit flag)
use_pooler = settings.is_supabase_pooler or ":6543" in settings.database_url

connect_args = {}
engine_kwargs: dict = {
    "echo": settings.app_env == "development" and False,
    "future": True,
}

if use_pooler:
    # Supavisor transaction pooler does not support prepared statements
    connect_args["statement_cache_size"] = 0
    connect_args["prepared_statement_cache_size"] = 0
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = connect_args
else:
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_health() -> bool:
    """Check database connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False
