from typing import Any

from celery import Celery
from celery.signals import worker_ready
from kombu import Exchange, Queue

from packages.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "applyon_workers",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "apps.workers.tasks.task_status",
        "apps.workers.tasks.jobs",
        "apps.workers.tasks.autopilot",
    ],
)

# Define all 10 isolated workload queues as per Section 18 of ARCHITECTURE.md
default_exchange = Exchange("applyon", type="direct")

celery_app.conf.task_queues = (
    Queue("job_ingestion", default_exchange, routing_key="job_ingestion"),
    Queue("embeddings", default_exchange, routing_key="embeddings"),
    Queue("ai_matching", default_exchange, routing_key="ai_matching"),
    Queue("document_generation", default_exchange, routing_key="document_generation"),
    Queue("form_schema", default_exchange, routing_key="form_schema"),
    Queue("browser_automation", default_exchange, routing_key="browser_automation"),
    Queue("autopilot", default_exchange, routing_key="autopilot"),
    Queue("notifications", default_exchange, routing_key="notifications"),
    Queue("maintenance", default_exchange, routing_key="maintenance"),
    Queue("priority", default_exchange, routing_key="priority"),
)

celery_app.conf.task_default_queue = "maintenance"
celery_app.conf.task_default_exchange = "applyon"
celery_app.conf.task_default_routing_key = "maintenance"

# Reliability settings
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Periodic schedule (run `celery -A apps.workers.celery_app beat`)
celery_app.conf.beat_schedule = {
    "discover-jobs-hourly": {"task": "jobs.discover_all", "schedule": 60 * 60},
    "match-users-every-30-min": {"task": "jobs.match_all_users", "schedule": 30 * 60},
    "autopilot-every-15-min": {"task": "autopilot.tick", "schedule": 15 * 60},
    "expire-stale-jobs-daily": {"task": "jobs.expire_stale", "schedule": 24 * 60 * 60},
}



@worker_ready.connect
def _discover_on_start(**_: Any) -> None:
    """A fresh deploy has no jobs yet; search once now instead of waiting for the hourly run."""
    celery_app.send_task("jobs.discover_all")


# Explicitly import tasks for registration
import apps.workers.tasks.autopilot  # noqa: F401, E402
import apps.workers.tasks.jobs  # noqa: F401, E402
import apps.workers.tasks.task_status  # noqa: F401, E402
