from celery import Celery
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

# Explicitly import tasks for registration
import apps.workers.tasks.jobs  # noqa: F401, E402
import apps.workers.tasks.task_status  # noqa: F401, E402
