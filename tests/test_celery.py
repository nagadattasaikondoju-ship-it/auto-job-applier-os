from apps.workers.celery_app import celery_app


def test_celery_queues_configuration() -> None:
    expected_queues = {
        "job_ingestion",
        "embeddings",
        "ai_matching",
        "document_generation",
        "form_schema",
        "browser_automation",
        "autopilot",
        "notifications",
        "maintenance",
        "priority",
    }
    actual_queues = {q.name for q in celery_app.conf.task_queues}
    assert expected_queues.issubset(actual_queues)


def test_celery_reliability_settings() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.timezone == "Asia/Kolkata"


def test_task_registered() -> None:
    assert "tasks.update_progress" in celery_app.tasks
