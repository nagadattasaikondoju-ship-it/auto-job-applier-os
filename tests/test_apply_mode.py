"""Auto-apply vs assisted apply: who submits, and what Approve does for each."""

import json
import uuid
from unittest.mock import patch

from sqlalchemy import select

from packages.core.database import async_session_maker
from packages.core.models.applications import Application
from packages.core.models.jobs import Company, Job
from packages.core.services.apply_mode import apply_ats, apply_mode, assisted_reason


def test_apply_mode_by_site() -> None:
    assert apply_mode("greenhouse", "https://boards.greenhouse.io/acme/jobs/1") == "auto"
    assert apply_mode("ashby", "https://jobs.ashbyhq.com/acme/1") == "auto"
    assert apply_mode("lever", "https://jobs.lever.co/acme/1/apply") == "assisted"
    assert apply_mode("workday", "https://acme.wd3.myworkdayjobs.com/x") == "assisted"
    # Aggregator jobs record 'unknown': the apply link decides
    assert apply_mode("unknown", "https://job-boards.greenhouse.io/acme/jobs/2") == "auto"
    assert apply_mode("unknown", "https://in.linkedin.com/jobs/view/3") == "assisted"
    assert apply_mode(None, None) == "assisted"
    assert apply_ats("unknown", "https://jobs.lever.co/acme/1") == "lever"
    assert "CAPTCHA" in assisted_reason("lever", None)


async def _make_application(user_id: str, url: str, ats: str) -> uuid.UUID:
    async with async_session_maker() as db:
        company = Company(name=f"Co {uuid.uuid4().hex[:6]}", normalized_name=uuid.uuid4().hex, ats_type=ats)
        db.add(company)
        await db.flush()
        job = Job(
            company_id=company.id, title="Data Analyst", normalized_title="data analyst", source=ats,
            external_id=uuid.uuid4().hex, application_url=url, ats_type=ats,
            description_text="SQL and Python.", content_hash=uuid.uuid4().hex,
        )
        db.add(job)
        await db.flush()
        app_obj = Application(
            user_id=user_id, job_id=job.id, status="ready_for_review", channel="assisted",
            application_url=url, notes=json.dumps({"fields": [], "unresolved_count": 0}),
        )
        db.add(app_obj)
        await db.commit()
        return app_obj.id


async def _status(app_id: uuid.UUID) -> tuple[str, str | None]:
    async with async_session_maker() as db:
        a = (await db.execute(select(Application).where(Application.id == app_id))).scalar_one()
        return a.status, a.failure_reason


async def test_approve_assisted_goes_to_handoff_without_browser(client) -> None:  # type: ignore[no-untyped-def]
    user = f"am-{uuid.uuid4().hex[:8]}"
    app_id = await _make_application(user, "https://jobs.lever.co/acme/123/apply", "lever")
    with patch("apps.workers.dispatch.enqueue_browser_submission") as enqueue:
        r = await client.post(f"/v1/review-queue/applications/{app_id}/approve", headers={"X-Dev-User-Id": user})
    assert r.status_code == 200, r.text
    assert r.json()["apply_mode"] == "assisted" and r.json()["submission_queued"] is False
    enqueue.assert_not_called()  # no doomed browser run against a CAPTCHA
    status, reason = await _status(app_id)
    assert status == "needs_user_action" and "CAPTCHA" in (reason or "")
    detail = (await client.get(f"/v1/applications/{app_id}", headers={"X-Dev-User-Id": user})).json()
    assert detail["apply_mode"] == "assisted" and detail["apply_ats"] == "lever"

    # The user finishes it on the site and confirms
    r = await client.patch(f"/v1/applications/{app_id}/status", json={"status": "submitted"}, headers={"X-Dev-User-Id": user})
    assert r.status_code == 200 and (await _status(app_id))[0] == "submitted"


async def test_approve_auto_queues_browser(client) -> None:  # type: ignore[no-untyped-def]
    user = f"am-{uuid.uuid4().hex[:8]}"
    app_id = await _make_application(user, "https://boards.greenhouse.io/acme/jobs/9", "greenhouse")
    with patch("apps.workers.dispatch.enqueue_browser_submission", return_value=True) as enqueue:
        r = await client.post(f"/v1/review-queue/applications/{app_id}/approve", headers={"X-Dev-User-Id": user})
    assert r.status_code == 200 and r.json()["apply_mode"] == "auto"
    enqueue.assert_called_once_with(str(app_id))
    assert (await _status(app_id))[0] == "approved"
