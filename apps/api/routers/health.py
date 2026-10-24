from fastapi import APIRouter, Response, status

from packages.core.config import settings
from packages.core.database import check_db_health
from packages.core.redis import check_redis_health

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Basic liveness probe."""
    return {
        "status": "ok",
        "env": settings.app_env,
    }


@router.get("/ready")
async def readiness(response: Response) -> dict[str, object]:
    """Readiness probe checking database and redis connectivity."""
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()

    is_ready = db_ok and redis_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if is_ready else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
    }
