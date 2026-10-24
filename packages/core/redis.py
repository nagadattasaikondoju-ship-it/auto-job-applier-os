import redis as sync_redis
from redis.asyncio import ConnectionPool, Redis

from packages.core.config import settings

_async_pool: ConnectionPool | None = None


def get_async_redis_pool() -> ConnectionPool:
    global _async_pool
    if _async_pool is None:
        _async_pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _async_pool


def get_async_redis() -> Redis:
    """Return an async Redis client."""
    return Redis(connection_pool=get_async_redis_pool())


def get_sync_redis() -> sync_redis.Redis:
    """Return a synchronous Redis client (for Celery workers)."""
    return sync_redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


async def check_redis_health() -> bool:
    """Ping Redis to verify connectivity."""
    try:
        client = get_async_redis()
        pong = await client.ping()
        return bool(pong)
    except Exception:
        return False


async def check_and_set_idempotency(idempotency_key: str, ttl_seconds: int = 86400) -> bool:
    """
    Check-and-set idempotency key.
    Returns True if the key is new and acquired; False if already processed.
    """
    if not idempotency_key:
        return True
    client = get_async_redis()
    key = f"idempotency:{idempotency_key}"
    is_new = await client.set(key, "processing", nx=True, ex=ttl_seconds)
    return bool(is_new)
