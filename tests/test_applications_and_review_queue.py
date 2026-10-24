"""Tests for Phase 6: Form schema extraction, answer resolution, applications tracker, and review queue."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.deps.db import get_db
from apps.api.main import app
from packages.core.models.applications import Application, ApplicationEvent
from packages.core.models.jobs import Company, Job, JobFormSchema
from packages.core.models.preferences import AnswerBank
from packages.core.models.profile import Profile
from packages.core.services.answer_resolver import (
    AnswerResolutionService,
    FieldDefinition,
)
from packages.core.services.applications import ApplicationsService
from packages.core.services.form_schema import (
    GreenhouseFormExtractor,
    LeverFormExtractor,
    infer_field_type_and_key,
)


def test_field_inference_and_canonical_mapping():
    """Verify inference of canonical keys and field types across various ATS formats."""
    ftype, key = infer_field_type_and_key("Notice period (in days)")
    assert key == "notice_period_days"
    assert ftype == "number"

    ftype, key = infer_field_type_and_key("Expected CTC (in LPA)")
    assert key == "expected_ctc_lpa"
    assert ftype == "number"

    ftype, key = infer_field_type_and_key("Attach Resume")
    assert key in ("resume", "resume_file")
    assert ftype == "file"

    ftype, key = infer_field_type_and_key("Why do you want to work at Swiggy?")
    assert ftype == "textarea"


def test_greenhouse_and_lever_extractors():
    """Test schema extraction from mock Greenhouse and Lever payloads."""
    gh_payload = {
        "questions": [
            {
                "id": 12345,
                "label": "Are you comfortable working in Bengaluru?",
                "required": True,
                "fields": [{"type": "multi_value_single_select", "values": ["Yes", "No"]}],
            }
        ]
    }
    gh_fields = GreenhouseFormExtractor.parse_api_payload(gh_payload)
    assert len(gh_fields) == 7  # 6 standard + 1 custom
    assert gh_fields[-1].field_id == "custom_question_12345"
    assert gh_fields[-1].field_type == "select"
    assert gh_fields[-1].options == ["Yes", "No"]

    lever_payload = {
        "customQuestions": [
            {
                "text": "What is your notice period?",
                "type": "text",
                "required": True,
            }
        ]
    }
    lever_fields = LeverFormExtractor.parse_api_payload(lever_payload)
    assert len(lever_fields) == 9  # 8 standard + 1 custom
    assert lever_fields[-1].canonical_key == "notice_period_days"


@pytest.mark.asyncio
async def test_answer_resolution_service():
    """Test multi-tier answer resolution: profile match, answer bank, and option matching."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"

    profile = Profile(
        user_id=user_id,
        full_name="Datta Sai",
        email="datta@example.com",
        phone="+919876543210",
        city="Bengaluru",
        notice_period_days=15,
        current_ctc_lpa=18.0,
        expected_ctc_lpa=24.0,
    )

    bank_entry = AnswerBank(
        id=uuid.uuid4(),
        user_id=user_id,
        question_key="preferred_shift",
        question_text="Preferred Work Shift",
        answer_text="Day Shift",
        source="questionnaire",
        times_used=2,
    )

    company = Company(
        id=uuid.uuid4(),
        name="Zomato",
        normalized_name="zomato",
        domain="zomato.com",
        careers_url="https://zomato.com/careers",
        ats_type="greenhouse",
    )
    job = Job(
        id=uuid.uuid4(),
        company_id=company.id,
        company=company,
        title="Backend Engineer",
        normalized_title="backend engineer",
        source="greenhouse",
        external_id="123",
        application_url="https://jobs.example.com/zomato/1",
        description_text="Looking for Python engineers.",
        content_hash="hash-123",
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [bank_entry]
    mock_db.execute.return_value = mock_result

    resolver = AnswerResolutionService(mock_db)
    fields = [
        FieldDefinition(field_id="first_name", label="First Name", canonical_key="first_name"),
        FieldDefinition(field_id="email", label="Email", canonical_key="email"),
        FieldDefinition(
            field_id="notice",
            label="Notice Period (Days)",
            canonical_key="notice_period_days",
            field_type="number",
        ),
        FieldDefinition(
            field_id="shift",
            label="Preferred Work Shift",
            canonical_key="preferred_shift",
            options=["Day Shift", "Night Shift"],
        ),
        FieldDefinition(
            field_id="unanswerable",
            label="What is your favorite space mission?",
            required=True,
            field_type="text",
        ),
    ]

    plan = await resolver.resolve_fields(user_id=user_id, profile=profile, job=job, fields=fields)

    assert plan.fields[0].value == "Datta"
    assert plan.fields[0].source == "profile"
    assert plan.fields[0].confidence == 1.0

    assert plan.fields[1].value == "datta@example.com"
    assert plan.fields[2].value == 15

    assert plan.fields[3].value == "Day Shift"
    assert plan.fields[3].source == "answer_bank"

    # Unanswerable question
    assert plan.unresolved_count >= 1
    assert plan.can_auto_submit is False


@pytest.mark.asyncio
async def test_applications_lifecycle_and_review_queue():
    """Test application creation, audit events, status transitions, and inline answer edits."""
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    app_id = uuid.uuid4()
    job_id = uuid.uuid4()

    profile = Profile(
        user_id=user_id,
        full_name="Rohan Sharma",
        email="rohan@example.com",
        phone="+919999999999",
        city="Hyderabad",
    )

    company = Company(
        id=uuid.uuid4(),
        name="Razorpay",
        normalized_name="razorpay",
        domain="razorpay.com",
        careers_url="https://razorpay.com/careers",
        ats_type="greenhouse",
    )
    job = Job(
        id=job_id,
        company_id=company.id,
        company=company,
        title="SDE-2",
        normalized_title="sde-2",
        source="greenhouse",
        external_id="999",
        application_url="https://boards.greenhouse.io/razorpay/jobs/999",
        ats_type="greenhouse",
        description_text="Build payment gateways.",
        content_hash="hash-999",
    )

    schema_json = [
        {"field_id": "first_name", "label": "First Name", "canonical_key": "first_name", "field_type": "text", "required": True, "options": []},
        {"field_id": "email", "label": "Email", "canonical_key": "email", "field_type": "email", "required": True, "options": []},
    ]

    form_schema = JobFormSchema(
        id=uuid.uuid4(),
        job_id=job_id,
        ats_type="greenhouse",
        schema_json=schema_json,
        extraction_method="generic",
        extracted_at=datetime.now(UTC),
        version=1,
        status="ready",
    )
    assert profile.full_name == "Rohan Sharma"
    assert form_schema.status == "ready"

    app_obj = Application(
        id=app_id,
        user_id=user_id,
        job_id=job_id,
        status="ready_for_review",
        channel="extension",
        application_url=job.application_url,
        notes=json.dumps({"fields": schema_json, "unresolved_count": 0, "can_auto_submit": True}),
        created_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Step 1: Status update
    svc = ApplicationsService(mock_db)

    # Mock execute for status lookup
    res_status = MagicMock()
    res_status.scalars.return_value.first.return_value = app_obj
    mock_db.execute.return_value = res_status

    updated = await svc.update_status(
        user_id=user_id,
        application_id=app_id,
        new_status="submitted",
        notes="Applied via Chrome extension",
    )
    assert updated.status == "submitted"
    assert updated.submitted_at is not None

    # Step 2: Detail lookup
    res_detail = MagicMock()
    res_detail.first.return_value = (app_obj, job)
    res_events = MagicMock()
    event = ApplicationEvent(
        id=uuid.uuid4(),
        application_id=app_id,
        type="created",
        payload={},
        actor="user",
        created_at=datetime.now(UTC),
    )
    res_events.scalars.return_value.all.return_value = [event]
    mock_db.execute.side_effect = [res_detail, res_events]

    detail = await svc.get_application_detail(user_id=user_id, application_id=app_id)
    assert detail["status"] == "submitted"
    assert detail["job"]["company_name"] == "Razorpay"
    assert len(detail["events"]) == 1

    # Step 3: Inline answer edit
    res_edit = MagicMock()
    res_edit.scalars.return_value.first.return_value = app_obj
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = res_edit

    plan_res = await svc.edit_answer(
        user_id=user_id,
        application_id=app_id,
        field_id="first_name",
        new_value="Rohan Kumar",
        save_to_answer_bank=True,
    )
    assert any(f["field_id"] == "first_name" and f["value"] == "Rohan Kumar" for f in plan_res["fields"])


@pytest.mark.asyncio
async def test_applications_api_endpoints():
    """Test FastAPI application and review queue endpoints with simulated auth."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    fake_job_id = uuid.uuid4()
    fake_app_id = uuid.uuid4()

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        with (
            patch(
                "packages.core.services.applications.ApplicationsService.create_or_get_application",
                new_callable=AsyncMock,
            ) as mock_create,
            patch(
                "packages.core.services.applications.ApplicationsService.list_applications",
                new_callable=AsyncMock,
            ) as mock_list,
            patch(
                "packages.core.services.applications.ApplicationsService.update_status",
                new_callable=AsyncMock,
            ) as mock_update,
        ):
            mock_app = MagicMock()
            mock_app.id = fake_app_id
            mock_app.status = "ready_for_review"
            mock_app.channel = "extension"
            mock_app.application_url = "https://example.com/apply"

            mock_plan = MagicMock()
            mock_plan.unresolved_count = 0
            mock_plan.can_auto_submit = True

            mock_create.return_value = (mock_app, mock_plan)
            mock_list.return_value = {
                "items": [
                    {
                        "id": str(fake_app_id),
                        "job_id": str(fake_job_id),
                        "job_title": "Full Stack Engineer",
                        "company_name": "CRED",
                        "location": "Bengaluru",
                        "salary_min_lpa": 20.0,
                        "salary_max_lpa": 35.0,
                        "status": "ready_for_review",
                        "channel": "extension",
                        "application_url": "https://example.com/apply",
                        "submitted_at": None,
                        "created_at": "2026-10-24T12:00:00Z",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20,
            }
            mock_update.return_value = mock_app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # 1. Create application
                create_resp = await ac.post(
                    "/v1/applications",
                    json={"job_id": str(fake_job_id), "channel": "extension"},
                    headers=headers,
                )
                assert create_resp.status_code == 201
                assert create_resp.json()["id"] == str(fake_app_id)

                # 2. List applications
                list_resp = await ac.get("/v1/applications", headers=headers)
                assert list_resp.status_code == 200
                assert list_resp.json()["total"] == 1

                # 3. Approve application
                approve_resp = await ac.post(
                    f"/v1/review-queue/applications/{fake_app_id}/approve",
                    headers=headers,
                )
                assert approve_resp.status_code == 200
                assert approve_resp.json()["approved"] is True

                # 4. Status transition
                status_resp = await ac.patch(
                    f"/v1/applications/{fake_app_id}/status",
                    json={"status": "interview", "notes": "HR Screening round scheduled"},
                    headers=headers,
                )
                assert status_resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
