import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routers import (
    analytics,
    answers,
    applications,
    ats,
    autopilot,
    consents,
    credits,
    documents,
    extension,
    health,
    jobs,
    matches,
    me,
    notifications,
    onboarding,
    preferences,
    privacy,
    profile,
    resumes,
    review_queue,
    tasks,
)
from packages.core.config import settings

app = FastAPI(
    title="Applyon API",
    description="Production-grade AI Job Application Copilot Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/v1/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time", "Idempotency-Key"],
)


@app.middleware("http")
async def add_process_time_and_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Measure request latency and add standard response headers."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Response-Time"] = f"{process_time_ms:.2f}ms"
    return response


# Standardized Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        error_detail = {
            "code": exc.detail.get("code", "ERROR"),
            "message": exc.detail.get("message", "An error occurred"),
            "details": exc.detail.get("details"),
        }
    else:
        error_detail = {
            "code": f"HTTP_{exc.status_code}",
            "message": str(exc.detail),
            "details": None,
        }
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_detail},
    )


def _validation_message(exc: RequestValidationError) -> str:
    """Name the fields that failed ("Please check: expected ctc lpa") so the user knows what to fix."""
    fields = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path") and not str(p).isdigit()]
        if loc:
            name = loc[-1].replace("_", " ")
            if name not in fields:
                fields.append(name)
    return f"Please check: {', '.join(fields)}" if fields else "Invalid request parameters"


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": _validation_message(exc),
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.app_env == "development" else None,
            }
        },
    )


# Health checks mounted at root and v1
app.include_router(health.router)
app.include_router(health.router, prefix="/v1")

# V1 API Routers
app.include_router(tasks.router, prefix="/v1")
app.include_router(me.router, prefix="/v1")
app.include_router(profile.router, prefix="/v1")
app.include_router(resumes.router, prefix="/v1")
app.include_router(onboarding.router, prefix="/v1")
app.include_router(consents.router, prefix="/v1")
app.include_router(answers.router, prefix="/v1")
app.include_router(jobs.router, prefix="/v1")
app.include_router(matches.router, prefix="/v1")
app.include_router(documents.router, prefix="/v1")
app.include_router(applications.router, prefix="/v1")
app.include_router(review_queue.router, prefix="/v1")
app.include_router(extension.router, prefix="/v1")
app.include_router(credits.router, prefix="/v1")
app.include_router(notifications.router, prefix="/v1")
app.include_router(analytics.router, prefix="/v1")
app.include_router(privacy.router, prefix="/v1")
app.include_router(ats.router, prefix="/v1")
app.include_router(preferences.router, prefix="/v1")
app.include_router(autopilot.router, prefix="/v1")
