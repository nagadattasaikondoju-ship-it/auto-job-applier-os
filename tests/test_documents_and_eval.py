"""Unit and integration tests for Phase 5: Document Generation, PDF Rendering, and Eval Harness."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.deps.db import get_db
from apps.api.main import app
from evals.eval_runner import run_golden_eval
from packages.documents.renderer import (
    generate_resume_filename,
    render_html,
    render_pdf,
)


def test_filename_generation() -> None:
    """Test standard resume filename output."""
    assert generate_resume_filename("Naga Datta Sai") == "Naga_Datta_Sai_Resume.pdf"
    assert generate_resume_filename("John Doe, Jr.") == "John_Doe_Jr_Resume.pdf"
    assert generate_resume_filename("") == "Candidate_Resume.pdf"


def test_html_and_pdf_rendering() -> None:
    """Test Jinja2 template compiling and PDF byte stream generation."""
    profile_data = {
        "full_name": "Naga Datta Sai",
        "email": "sai@applyon.in",
        "phone": "+91 9876543210",
        "city": "Bengaluru",
        "country": "India",
        "summary": "Experienced full-stack engineer building AI systems.",
        "skills": [{"name": "Python"}, {"name": "React"}, {"name": "FastAPI"}],
        "experiences": [
            {
                "title": "Senior Engineer",
                "company": "Tech Corp",
                "location": "Bengaluru",
                "start_date": "2023",
                "end_date": "Present",
                "is_current": True,
                "bullets": [{"text": "Engineered scalable microservices processing 10k req/s"}],
            }
        ],
    }

    tailored_data = {
        "summary": "AI-focused software developer with microservices background.",
        "skills_ordered": ["FastAPI", "Python", "React"],
        "experiences": profile_data["experiences"],
    }

    html_out = render_html(
        "classic_ats.html",
        {"profile": profile_data, "tailored": tailored_data},
    )
    assert "Naga Datta Sai" in html_out
    assert "Core Competencies & Skills" in html_out
    assert "Engineered scalable microservices" in html_out

    # Render PDF bytes
    pdf_bytes = render_pdf(html_out)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


def test_golden_dataset_eval_harness() -> None:
    """Run golden eval suite and verify zero fabrication rate (0.0%)."""
    eval_results = run_golden_eval()
    assert eval_results["passed"] is True
    assert eval_results["fabrication_rate"] == 0.0
    assert eval_results["caught_fabrications"] == eval_results["total_adversarial_cases"]
    assert eval_results["matching_accuracy"] >= 0.90


@pytest.mark.asyncio
async def test_documents_api_endpoints() -> None:
    """Test document tailoring and detail endpoints."""
    headers = {"X-Dev-User-Id": "dev-user-123"}
    fake_job_id = uuid.uuid4()
    fake_resume_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    no_row = MagicMock()
    no_row.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = no_row

    # Mock resume version record
    mock_ver = MagicMock()
    mock_ver.id = fake_resume_id
    mock_ver.job_id = fake_job_id
    mock_ver.version_no = 1
    mock_ver.truth_check_status = "passed"
    mock_ver.flagged_claims = []
    mock_ver.content_json = {"summary": "Tailored engineer"}
    mock_ver.status = "approved"
    mock_ver.created_at = MagicMock()
    mock_ver.created_at.isoformat.return_value = "2026-10-24T12:00:00Z"

    # Mock cover letter record
    mock_cl = MagicMock()
    mock_cl.id = uuid.uuid4()
    mock_cl.text = "Dear Hiring Team..."
    mock_cl.pdf_path = "/tmp/cl.pdf"

    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        with (
            patch(
                "apps.api.routers.documents.tailor_resume_for_job",
                new_callable=AsyncMock,
            ) as mock_tailor,
            patch(
                "apps.api.routers.documents.generate_cover_letter",
                new_callable=AsyncMock,
            ) as mock_cl_gen,
        ):
            mock_tailor.return_value = (mock_ver, "/tmp/resume.pdf")
            mock_cl_gen.return_value = mock_cl

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                tailor_resp = await ac.post(
                    f"/v1/jobs/{fake_job_id}/tailor",
                    headers=headers,
                )
                assert tailor_resp.status_code == 201
                data = tailor_resp.json()
                assert data["status"] == "ready"
                assert "resume_version" in data
                assert data["resume_version"]["id"] == str(fake_resume_id)
                assert data["resume_version"]["truth_check_status"] == "passed"
    finally:
        app.dependency_overrides.pop(get_db, None)
