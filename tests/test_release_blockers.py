"""Release blockers from the production audit: duplicate submissions, status transitions,
SSRF in job import, and free credits."""

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from packages.core import net_safety
from packages.core.database import async_session_maker
from packages.core.models.applications import Application
from packages.core.models.jobs import Company, Job
from packages.core.services.applications import user_transition_error


def h(uid: str) -> dict[str, str]:
    return {"X-Dev-User-Id": uid}


async def _app(user_id: str, status: str = "ready_for_review", submitted: bool = False) -> uuid.UUID:
    url = f"https://boards.greenhouse.io/acme/jobs/{uuid.uuid4().int % 10**8}"
    async with async_session_maker() as db:
        company = Company(name=f"Co {uuid.uuid4().hex[:6]}", normalized_name=uuid.uuid4().hex, ats_type="greenhouse")
        db.add(company)
        await db.flush()
        job = Job(company_id=company.id, title="Backend Engineer", normalized_title="backend engineer", source="greenhouse",
                  external_id=uuid.uuid4().hex, application_url=url, ats_type="greenhouse", content_hash=uuid.uuid4().hex)
        db.add(job)
        await db.flush()
        a = Application(user_id=user_id, job_id=job.id, status=status, channel="autopilot", application_url=url,
                        notes=json.dumps({"fields": [], "unresolved_count": 0}))
        if submitted:
            from datetime import UTC, datetime
            a.submitted_at = datetime.now(UTC)
        db.add(a)
        await db.commit()
        return a.id


async def _status(app_id: uuid.UUID) -> str:
    async with async_session_maker() as db:
        return (await db.execute(select(Application.status).where(Application.id == app_id))).scalar_one()


# ---------------------------------------------------------------- duplicate submissions

async def test_simultaneous_approvals_enqueue_one_submission(client: AsyncClient) -> None:
    uid = f"rb-{uuid.uuid4().hex[:8]}"
    app_id = await _app(uid)
    with patch("apps.workers.dispatch.enqueue_browser_submission", return_value=True) as enqueue:
        rs = await asyncio.gather(*[client.post(f"/v1/review-queue/applications/{app_id}/approve", headers=h(uid)) for _ in range(5)])
    codes = sorted(r.status_code for r in rs)
    assert codes.count(200) == 1 and codes.count(409) == 4, [r.text for r in rs]
    enqueue.assert_called_once_with(str(app_id))
    assert await _status(app_id) == "approved"


async def test_approving_a_submitted_application_is_refused(client: AsyncClient) -> None:
    uid = f"rb-{uuid.uuid4().hex[:8]}"
    app_id = await _app(uid, status="submitted", submitted=True)
    with patch("apps.workers.dispatch.enqueue_browser_submission") as enqueue:
        r = await client.post(f"/v1/review-queue/applications/{app_id}/approve", headers=h(uid))
    assert r.status_code == 409 and "already submitted" in r.text
    enqueue.assert_not_called()


async def test_worker_submits_once_even_if_run_twice() -> None:
    from apps.workers.tasks import autopilot as worker

    app_id = await _app(f"rb-{uuid.uuid4().hex[:8]}", status="approved")
    calls = 0

    async def fake_execute(*_: Any, **__: Any) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.2)
        return SimpleNamespace(status="submitted", blocker_detected=None, proof_screenshot_path=None, fields_filled=3, error_message=None)

    with (
        patch.object(worker.BrowserAutomationExecutor, "execute_application", side_effect=fake_execute),
        patch.object(worker, "_write_resume_pdf", AsyncMock(return_value=None)),
    ):
        results = await asyncio.gather(
            worker._async_execute_browser_application(str(app_id)), worker._async_execute_browser_application(str(app_id))
        )
    assert calls == 1
    assert sum(1 for r in results if r.get("skipped")) == 1
    assert await _status(app_id) == "submitted"


async def test_worker_crash_does_not_leave_submitting() -> None:
    from apps.workers.tasks import autopilot as worker

    app_id = await _app(f"rb-{uuid.uuid4().hex[:8]}", status="approved")
    with (
        patch.object(worker.BrowserAutomationExecutor, "execute_application", side_effect=RuntimeError("browser died")),
        patch.object(worker, "_write_resume_pdf", AsyncMock(return_value=None)),
        pytest.raises(RuntimeError),
    ):
        await worker._async_execute_browser_application(str(app_id))
    assert await _status(app_id) == "failed"


# ---------------------------------------------------------------- status transitions

def test_transition_rules() -> None:
    def app(status: str, submitted: bool = False) -> Any:
        return SimpleNamespace(status=status, submitted_at=object() if submitted else None)

    assert user_transition_error(app("ready_for_review"), "offer")
    assert user_transition_error(app("ready_for_review"), "interview")
    assert user_transition_error(app("ready_for_review"), "approved")  # only Approve does that
    assert user_transition_error(app("submitting"), "withdrawn")       # in flight
    assert user_transition_error(app("ready_for_review"), "submitted") is None  # applied myself
    assert user_transition_error(app("submitted", True), "interview") is None
    assert user_transition_error(app("interview", True), "offer") is None
    assert user_transition_error(app("rejected", True), "interview") is None  # correcting a mistake
    assert user_transition_error(app("ready_for_review"), "withdrawn") is None


async def test_status_endpoint_enforces_transitions(client: AsyncClient) -> None:
    uid = f"rb-{uuid.uuid4().hex[:8]}"
    app_id = await _app(uid)
    url = f"/v1/applications/{app_id}/status"
    r = await client.patch(url, json={"status": "offer"}, headers=h(uid))
    assert r.status_code == 409 and "submitted first" in r.text
    assert await _status(app_id) == "ready_for_review"
    assert (await client.patch(url, json={"status": "submitted"}, headers=h(uid))).status_code == 200
    assert (await client.patch(url, json={"status": "interview"}, headers=h(uid))).status_code == 200
    assert (await client.patch(url, json={"status": "offer"}, headers=h(uid))).status_code == 200


# ---------------------------------------------------------------- SSRF

@pytest.fixture
def fake_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    table = {"jobs.example.com": ["93.184.215.14"], "evil.example.com": ["10.0.0.7"], "rebind.example.com": ["93.184.215.14", "127.0.0.1"]}

    async def resolve(host: str, port: int) -> list[str]:
        if host in table:
            return table[host]
        return [host]  # IP literals resolve to themselves

    monkeypatch.setattr(net_safety, "_resolve", resolve)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/health/live", "http://169.254.169.254/latest/meta-data/", "http://10.1.2.3/", "http://[::1]/",
    "http://evil.example.com/job", "http://rebind.example.com/job", "file:///etc/passwd", "ftp://jobs.example.com/x",
    "https://jobs.example.com:8443/x", "https://user:pw@jobs.example.com/x", "http://[::ffff:127.0.0.1]/",
])
async def test_private_and_odd_urls_refused(url: str, fake_dns: None) -> None:
    with pytest.raises(net_safety.UnsafeUrlError):
        await net_safety.ensure_public_url(url)


async def test_public_url_allowed(fake_dns: None) -> None:
    assert await net_safety.ensure_public_url("https://jobs.example.com/careers/1") == "https://jobs.example.com/careers/1"


async def test_redirect_to_internal_address_is_not_followed(fake_dns: None) -> None:
    hit: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        hit.append(str(req.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        with pytest.raises(net_safety.UnsafeUrlError):
            await net_safety.safe_get(c, "https://jobs.example.com/job/1")
    assert hit == ["https://jobs.example.com/job/1"]  # the internal address was never requested


async def test_import_endpoint_rejects_internal_addresses(client: AsyncClient) -> None:
    for url in ["http://127.0.0.1:8000/health/live", "http://169.254.169.254/latest/meta-data/"]:
        r = await client.post("/v1/jobs/import", json={"url": url}, headers=h("rb-ssrf"))
        assert r.status_code == 422, (url, r.text)
    async with async_session_maker() as db:
        stored = (await db.execute(select(Job.id).where(Job.application_url.like("http://169.254.169.254%")))).first()
    assert stored is None


# ---------------------------------------------------------------- free credits

async def test_demo_topup_absent_in_production(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.api.deps.auth import AuthenticatedUser, get_current_user
    from apps.api.main import app
    from packages.core.config import settings

    # Production turns off dev logins, so sign the request in directly
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(user_id="rb-prod", email="", role="authenticated", claims={})
    monkeypatch.setattr(settings, "app_env", "production")
    try:
        r = await client.post("/v1/credits/topup-demo", json={"amount": 10})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 404


async def test_demo_topup_capped_in_development(client: AsyncClient) -> None:
    uid = f"rb-{uuid.uuid4().hex[:6]}"
    assert (await client.post("/v1/credits/topup-demo", json={"amount": 1000}, headers=h(uid))).status_code == 422
    assert (await client.post("/v1/credits/topup-demo", json={"amount": 10}, headers=h(uid))).status_code == 200


# ---------------------------------------------------------------- account deletion

async def test_deleted_account_stops_autopilot_and_unsent_applications(client: AsyncClient) -> None:
    from packages.core.models.applications import Campaign

    uid = f"rb-{uuid.uuid4().hex[:8]}"
    unsent = await _app(uid)
    sent = await _app(uid, status="submitted", submitted=True)
    async with async_session_maker() as db:
        db.add(Campaign(user_id=uid, preferences_snapshot={}, status="active"))
        await db.commit()
    assert (await client.delete("/v1/privacy/delete-account", headers=h(uid))).status_code == 200
    assert await _status(unsent) == "withdrawn"
    assert await _status(sent) == "submitted"  # history is kept, only anonymized
    async with async_session_maker() as db:
        statuses = (await db.execute(select(Campaign.status).where(Campaign.user_id == uid))).scalars().all()
    assert statuses == ["stopped"]
