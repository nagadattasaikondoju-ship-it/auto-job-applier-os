"""Fire-and-forget task dispatch that never blocks or breaks an API request.

When Redis/Celery isn't running (e.g. local front-end development) the task is skipped and
the application simply stays in its current state.
"""

import logging

logger = logging.getLogger("applyon.dispatch")


def enqueue_browser_submission(application_id: str) -> bool:
    try:
        from apps.workers.tasks.autopilot import execute_browser_application

        execute_browser_application.apply_async(args=[application_id], kwargs={"dry_run": False}, retry=False)
        return True
    except Exception as e:
        logger.info("Browser submission not enqueued for %s: %s", application_id, e)
        return False
