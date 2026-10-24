"""Tests for Phase 10: Notifications, Analytics, and DPDP Act 2023 Privacy Compliance."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.deps.db import get_db
from apps.api.main import app
from packages.core.models.applications import Application
from packages.core.models.platform import Notification
from packages.core.models.profile import Profile
from packages.core.services.notifications import NotificationsService


@pytest.mark.asyncio
async def test_notifications_service_and_email_delivery():
    """Verify transactional email sending and in-app notifications lifecycle."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    # Test simulated email delivery
    email_res = await NotificationsService.send_email(
        to_email="candidate@applyon.in",
        subject="Interview Invitation",
        html_body="<p>You have an interview scheduled.</p>",
        simulate=True,
    )
    assert email_res.get("simulated") is True
    assert "sim_" in email_res.get("id")

    # Test create notification
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    res_prof = MagicMock()
    res_prof.scalar_one_or_none.return_value = Profile(
        user_id=user_id,
        full_name="Aarav Sharma",
        email="aarav@example.com",
    )
    mock_db.execute.return_value = res_prof

    notif = await NotificationsService.create_notification(
        db=mock_db,
        user_id=user_id,
        notif_type="review_ready",
        title="Application Ready",
        body="Please review your application.",
        data={"app_id": "123"},
        channels=["in_app", "email"],
    )
    assert notif.user_id == user_id
    assert notif.type == "review_ready"
    assert "in_app" in notif.channels
    assert "email" in notif.channels


@pytest.mark.asyncio
async def test_notifications_api_endpoints():
    """Test /v1/notifications endpoints."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    notif_id = uuid.uuid4()

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    fake_notif = Notification(
        id=notif_id,
        user_id="dev-user-123",
        type="review_ready",
        title="Ready for review",
        body="Review now",
        data={},
        read_at=None,
        created_at=datetime.now(UTC),
    )

    try:
        with (
            patch("packages.core.services.notifications.NotificationsService.list_notifications", new_callable=AsyncMock) as mock_list,
            patch("packages.core.services.notifications.NotificationsService.mark_as_read", new_callable=AsyncMock) as mock_read,
            patch("packages.core.services.notifications.NotificationsService.mark_all_read", new_callable=AsyncMock) as mock_read_all,
        ):
            mock_list.return_value = ([fake_notif], 1)
            mock_read.return_value = fake_notif
            mock_read_all.return_value = 5

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. List
                res = await client.get("/v1/notifications", headers=headers)
                assert res.status_code == 200
                data = res.json()
                assert data["unread_count"] == 1
                assert len(data["items"]) == 1

                # 2. Mark specific read
                res_read = await client.post(f"/v1/notifications/{notif_id}/read", headers=headers)
                assert res_read.status_code == 200
                assert res_read.json()["id"] == str(notif_id)

                # 3. Mark all read
                res_all = await client.post("/v1/notifications/read-all", headers=headers)
                assert res_all.status_code == 200
                assert res_all.json()["marked_read_count"] == 5

    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_analytics_service_and_endpoints():
    """Verify overview and funnel calculation and API responses."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with (
            patch("packages.core.services.analytics.AnalyticsService.get_user_overview", new_callable=AsyncMock) as mock_overview,
            patch("packages.core.services.analytics.AnalyticsService.get_conversion_funnel", new_callable=AsyncMock) as mock_funnel,
        ):
            mock_overview.return_value = {
                "total_applications": 20,
                "total_submitted": 15,
                "total_interviews": 3,
                "total_offers": 1,
                "status_distribution": {"submitted": 11, "interview": 3, "offer": 1, "failed": 5},
                "credits": {"available_balance": 45, "daily_remaining": 8, "daily_limit": 10},
                "ai_usage": {"tokens_in": 12000, "tokens_out": 4000, "total_tokens": 16000, "estimated_cost_usd": 0.008},
                "profile_completeness_score": 95,
                "can_start_autopilot": True,
            }

            mock_funnel.return_value = {
                "stages": [
                    {"stage": "matched", "count": 100, "conversion_pct": 100.0},
                    {"stage": "reviewed", "count": 25, "conversion_pct": 25.0},
                    {"stage": "submitted", "count": 15, "conversion_pct": 60.0},
                    {"stage": "interview", "count": 3, "conversion_pct": 20.0},
                    {"stage": "offer", "count": 1, "conversion_pct": 33.3},
                ],
                "overall_conversion_pct": 6.7,
            }

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res_ov = await client.get("/v1/analytics/overview", headers=headers)
                assert res_ov.status_code == 200
                assert res_ov.json()["total_applications"] == 20
                assert res_ov.json()["credits"]["available_balance"] == 45

                res_fn = await client.get("/v1/analytics/funnel", headers=headers)
                assert res_fn.status_code == 200
                assert len(res_fn.json()["stages"]) == 5
                assert res_fn.json()["overall_conversion_pct"] == 6.7

    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_privacy_export_and_right_to_be_forgotten():
    """Verify DPDP Act 2023 full data export and right-to-be-forgotten deletion."""
    headers = {"X-Dev-User-Id": "dev-user-dpdp"}
    user_id = "dev-user-dpdp"

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Setup profile & data returns for export
    profile = Profile(
        user_id=user_id,
        full_name="Vikram Malhotra",
        email="vikram@example.com",
        city="Bengaluru",
        phone="+919876543212",
        headline="Full Stack Engineer",
        summary="Building web apps",
        work_authorization={"India": True},
        links={"github": "https://github.com/vikram"},
    )
    res_prof = MagicMock()
    res_prof.scalar_one_or_none.return_value = profile

    res_empty_list = MagicMock()
    res_empty_list.scalars.return_value.all.return_value = []

    res_app = Application(
        id=uuid.uuid4(),
        user_id=user_id,
        job_id=uuid.uuid4(),
        application_url="https://jobs.lever.co/test/123",
        status="submitted",
        channel="auto",
        created_at=datetime.now(UTC),
        submitted_at=datetime.now(UTC),
    )
    res_apps_list = MagicMock()
    res_apps_list.scalars.return_value.all.return_value = [res_app]

    # Query sequence for export:
    # 1. Profile
    # 2. Experiences
    # 3. Educations
    # 4. Skills
    # 5. Projects
    # 6. Certifications
    # 7. AnswerBank
    # 8. QuestionnaireSession
    # 9. ResumeVersion
    # 10. CoverLetter
    # 11. Application
    # 12. Consent
    mock_db.execute.side_effect = [
        res_prof,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_empty_list,
        res_apps_list,
        res_empty_list,
    ]

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. DPDP Export
            export_resp = await client.post("/v1/privacy/export", headers=headers)
            assert export_resp.status_code == 200
            export_data = export_resp.json()
            assert export_data["metadata"]["jurisdiction"] == "India (DPDP Act 2023)"
            assert export_data["profile"]["full_name"] == "Vikram Malhotra"
            assert export_data["profile"]["email"] == "vikram@example.com"
            assert len(export_data["applications"]) == 1

            # 2. DPDP Right to be Forgotten Deletion
            # Reset side effects for deletion executes:
            mock_db.execute.side_effect = None
            mock_db.execute.return_value = MagicMock()

            delete_resp = await client.delete("/v1/privacy/delete-account", headers=headers)
            assert delete_resp.status_code == 200
            del_data = delete_resp.json()
            assert del_data["status"] == "account_deleted"
            assert "securely deleted and anonymized" in del_data["message"]
            assert mock_db.commit.called

    finally:
        app.dependency_overrides.pop(get_db, None)
