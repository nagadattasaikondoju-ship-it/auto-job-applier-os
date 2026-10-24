"""Celery worker tasks namespace."""

from apps.workers.tasks.autopilot import autopilot_tick, execute_browser_application
from apps.workers.tasks.jobs import (
    crawl_adzuna_feed,
    crawl_ashby_board,
    crawl_greenhouse_board,
    crawl_lever_company,
    match_user_jobs,
)
from apps.workers.tasks.task_status import update_task_progress

__all__ = [
    "crawl_greenhouse_board",
    "crawl_lever_company",
    "crawl_ashby_board",
    "crawl_adzuna_feed",
    "match_user_jobs",
    "autopilot_tick",
    "execute_browser_application",
    "update_task_progress",
]
