"""Tests for Phase 7: Chrome Extension (MV3) fill-plan generation and proof-of-submission recording."""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.deps.db import get_db
from apps.api.main import app
from packages.core.models.applications import Application
from packages.core.models.jobs import Company, Job


def test_extension_manifest_and_files():
    """Verify Chrome Extension Manifest V3 structure and component file paths."""
    ext_dir = Path("apps/extension")
    manifest_file = ext_dir / "manifest.json"
    assert manifest_file.exists()

    with open(manifest_file, encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["manifest_version"] == 3
    assert manifest["name"] == "Applyon — AI Job Application Copilot"
    assert "activeTab" in manifest["permissions"]
    assert "storage" in manifest["permissions"]

    # Verify background and content script files exist
    assert (ext_dir / "background.js").exists()
    assert (ext_dir / "content.js").exists()
    assert (ext_dir / "popup" / "popup.html").exists()
    assert (ext_dir / "popup" / "popup.js").exists()


@pytest.mark.asyncio
async def test_extension_fill_plan_endpoint():
    """Test GET /v1/extension/fill-plan provides resolved form fields and ATS detection."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    fake_job_id = uuid.uuid4()
    fake_app_id = uuid.uuid4()
    apply_url = "https://boards.greenhouse.io/postman/jobs/8888"

    company = Company(
        id=uuid.uuid4(),
        name="Postman",
        normalized_name="postman",
        domain="postman.com",
        careers_url="https://postman.com/careers",
        ats_type="greenhouse",
    )
    job = Job(
        id=fake_job_id,
        company_id=company.id,
        company=company,
        title="Software Engineer",
        normalized_title="software engineer",
        source="greenhouse",
        external_id="8888",
        application_url=apply_url,
        ats_type="greenhouse",
        description_text="Build developer tools.",
        content_hash="hash-8888",
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # Mock finding existing job
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = job
        mock_db.execute.return_value = mock_res

        with patch(
            "packages.core.services.applications.ApplicationsService.create_or_get_application",
            new_callable=AsyncMock,
        ) as mock_app_svc:
            mock_app = MagicMock()
            mock_app.id = fake_app_id
            mock_app.resume_version_id = uuid.uuid4()

            mock_field = MagicMock()
            mock_field.model_dump.return_value = {
                "field_id": "email",
                "label": "Email",
                "canonical_key": "email",
                "field_type": "email",
                "required": True,
                "value": "candidate@example.com",
                "source": "profile",
                "confidence": 1.0,
                "needs_review": False,
                "dom_selector": "input#email",
            }

            mock_plan = MagicMock()
            mock_plan.can_auto_submit = True
            mock_plan.unresolved_count = 0
            mock_plan.fields = [mock_field]

            mock_app_svc.return_value = (mock_app, mock_plan)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.get(
                    f"/v1/extension/fill-plan?url={apply_url}",
                    headers=headers,
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["ats_type"] == "greenhouse"
                assert data["company_name"] == "Postman"
                assert data["job_title"] == "Software Engineer"
                assert len(data["fields"]) == 1
                assert data["fields"][0]["value"] == "candidate@example.com"
                assert data["can_auto_submit"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_extension_mark_submitted_endpoint():
    """Test POST /v1/extension/mark-submitted updates status with extension audit actor."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    fake_app_id = uuid.uuid4()

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        mock_app = MagicMock()
        mock_app.id = fake_app_id
        mock_app.user_id = "dev-user-123"
        mock_app.application_url = "https://boards.greenhouse.io/postman/jobs/8888"

        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = mock_app
        mock_db.execute.return_value = mock_res

        with patch(
            "packages.core.services.applications.ApplicationsService.update_status",
            new_callable=AsyncMock,
        ) as mock_update:
            updated_app = Application(
                id=fake_app_id,
                user_id="dev-user-123",
                job_id=uuid.uuid4(),
                status="submitted",
                channel="extension",
                application_url="https://boards.greenhouse.io/postman/jobs/8888",
            )
            mock_update.return_value = updated_app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/v1/extension/mark-submitted",
                    json={
                        "application_id": str(fake_app_id),
                        "proof_url": "https://boards.greenhouse.io/postman/jobs/8888/confirmation",
                        "proof_text": "Thank you for applying",
                    },
                    headers=headers,
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "submitted"
                assert data["success"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
