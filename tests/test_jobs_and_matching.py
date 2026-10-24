"""Unit and integration tests for Phase 4: Job Ingestion, ATS Detection, and Matching Funnel."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app
from packages.core.services.jobs import compute_preference_bucket_keys
from packages.jobs_sources.base import RawJob
from packages.jobs_sources.detector import detect_ats
from packages.jobs_sources.greenhouse import GreenhouseBoardConnector
from packages.jobs_sources.normalizer import (
    check_is_suspicious,
    clean_url,
    compute_content_hash,
    detect_remote_mode,
    extract_experience_range,
    extract_salary_lpa,
    extract_seniority,
    normalize_locations,
)


def test_ats_detection() -> None:
    """Test URL pattern detection for major ATS vendors."""
    assert detect_ats("https://boards.greenhouse.io/stripe/jobs/12345") == "greenhouse"
    assert detect_ats("https://job-boards.greenhouse.io/figma/jobs/6789") == "greenhouse"
    assert detect_ats("https://jobs.lever.co/postman/abcd-1234") == "lever"
    assert detect_ats("https://jobs.ashbyhq.com/linear/5678") == "ashby"
    assert detect_ats("https://adobe.myworkdayjobs.com/en-US/careers/job/123") == "workday"
    assert detect_ats("https://jobs.smartrecruiters.com/Visa/7439999") == "smartrecruiters"
    assert detect_ats("https://apply.workable.com/cred/j/ABC123") == "workable"
    assert detect_ats("https://example.com/careers") == "unknown"


def test_job_normalization_helpers() -> None:
    """Test text, seniority, location, and salary normalization logic."""
    # Seniority extraction
    clean_title, seniority = extract_seniority("Senior Backend Engineer")
    assert seniority == "senior"
    assert "senior" not in clean_title

    clean_title, seniority = extract_seniority("Software Engineer Intern")
    assert seniority == "intern"

    # Location normalization with Indian city alias mapping
    locs = normalize_locations("Bangalore / Gurgaon")
    assert "Bengaluru" in locs
    assert "Gurugram" in locs

    # Salary parsing
    sal_min, sal_max = extract_salary_lpa("Compensation: 15 - 25 LPA based on experience")
    assert sal_min == 15.0
    assert sal_max == 25.0

    # Experience range parsing
    exp_min, exp_max = extract_experience_range("Looking for 3 to 5 years experience in Python")
    assert exp_min == 3
    assert exp_max == 5

    # Remote mode classification
    assert detect_remote_mode("Role is fully Remote anywhere in India") == "remote"
    assert detect_remote_mode("Hybrid work model (3 days in office)") == "hybrid"
    assert detect_remote_mode("Onsite at our Bengaluru office") == "onsite"


def test_scam_filter_and_content_hash() -> None:
    """Test scam detection and deterministic content hashing."""
    # Scam detection
    is_scam, score = check_is_suspicious(
        title="Data Entry Operator",
        description="Immediate joining! Send CV to whatsapp only. Registration fee Rs 500 mandatory.",
        company="Global Tech",
        salary_max_lpa=None,
    )
    assert is_scam is True
    assert score == 0

    # Clean job
    is_scam_clean, clean_score = check_is_suspicious(
        title="Frontend Engineer",
        description="We are looking for an experienced React developer with deep TypeScript knowledge to build high-performance, scalable web applications for our platform.",
        company="Razorpay",
        salary_max_lpa=25.0,
    )
    assert is_scam_clean is False
    assert clean_score >= 80

    # Content hash determinism and tracking parameter stripping
    url1 = "https://boards.greenhouse.io/stripe/jobs/123?utm_source=linkedin&utm_medium=jobboard"
    url2 = "https://boards.greenhouse.io/stripe/jobs/123"
    assert clean_url(url1) == clean_url(url2)

    hash1 = compute_content_hash("Stripe", "software engineer", "Bengaluru", url1)
    hash2 = compute_content_hash("Stripe", "software engineer", "Bengaluru", url2)
    assert hash1 == hash2


def test_preference_bucket_keys() -> None:
    """Test indexed preference bucket generation for fast matching."""
    keys = compute_preference_bucket_keys(
        role="Backend Engineer",
        seniority="mid",
        locations=["Bengaluru", "Hyderabad"],
        is_remote=True,
    )
    assert "backend_engineer:mid:remote" in keys
    assert "backend_engineer:mid:bengaluru" in keys
    assert "backend_engineer:mid:hyderabad" in keys


def test_greenhouse_connector_normalization() -> None:
    """Test Greenhouse connector normalizing raw payload."""
    connector = GreenhouseBoardConnector(board_token="razorpay", company_name="Razorpay")
    raw = RawJob(
        source="greenhouse",
        external_id="1001",
        company_name="Razorpay",
        title="Senior Software Engineer - Payments",
        location_raw="Bangalore, India",
        application_url="https://boards.greenhouse.io/razorpay/jobs/1001",
        description_raw="<p>Build real-time payment APIs with Go and Python. Requires 4-7 years experience.</p>",
    )
    job_in = connector.normalize(raw)
    assert job_in.source == "greenhouse"
    assert job_in.company_name == "Razorpay"
    assert job_in.seniority == "senior"
    assert "Bengaluru" in job_in.locations
    assert job_in.experience_min == 4
    assert job_in.experience_max == 7
    assert job_in.ats_type == "greenhouse"
    assert job_in.content_hash != ""


@pytest.mark.asyncio
async def test_jobs_api_endpoints() -> None:
    """Test jobs feed and manual import API routes."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from apps.api.deps.db import get_db

    headers = {"X-Dev-User-Id": "dev-user-123"}
    fake_job_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock execute for matches router
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    try:
        with (
            patch("apps.api.routers.jobs.get_jobs_feed", new_callable=AsyncMock) as mock_feed,
            patch(
                "apps.api.routers.jobs.ingest_normalized_job", new_callable=AsyncMock
            ) as mock_ingest,
        ):
            mock_feed.return_value = [
                {
                    "id": str(fake_job_id),
                    "title": "Senior Backend Engineer",
                    "company": "Razorpay",
                    "location": "Bengaluru",
                    "posted_at": "2026-10-24T12:00:00Z",
                }
            ]

            mock_job = MagicMock()
            mock_job.id = fake_job_id
            mock_job.title = "Senior Developer"
            mock_job.ats_type = "lever"
            mock_job.application_url = "https://jobs.lever.co/postman/12345"
            mock_ingest.return_value = (mock_job, True)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Test jobs feed
                feed_resp = await ac.get("/v1/jobs", headers=headers)
                assert feed_resp.status_code == 200
                feed_data = feed_resp.json()
                assert "items" in feed_data
                assert feed_data["count"] == 1

                # Test manual job import
                import_resp = await ac.post(
                    "/v1/jobs/import",
                    json={
                        "url": "https://jobs.lever.co/postman/12345-senior-dev",
                        "optional_text": "Postman is looking for a Senior Developer with 5+ years experience in Node.js.",
                    },
                    headers=headers,
                )
                assert import_resp.status_code == 201
                import_data = import_resp.json()
                assert import_data["job_id"] == str(fake_job_id)
                assert import_data["ats_type"] == "lever"

                # Test matches list
                matches_resp = await ac.get("/v1/matches", headers=headers)
                assert matches_resp.status_code == 200
                assert "items" in matches_resp.json()
    finally:
        app.dependency_overrides.pop(get_db, None)
