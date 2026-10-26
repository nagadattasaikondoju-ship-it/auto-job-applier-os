"""Greenhouse job board connector using official public boards API."""

import contextlib
import html
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from packages.jobs_sources.base import BaseJobConnector, JobIn, RawJob
from packages.jobs_sources.normalizer import (
    check_is_suspicious,
    clean_url,
    compute_content_hash,
    detect_remote_mode,
    extract_experience_range,
    extract_salary_lpa,
    extract_seniority,
    extract_skills_from_text,
    normalize_locations,
)

logger = logging.getLogger("applyon.jobs.greenhouse")


class GreenhouseBoardConnector(BaseJobConnector):
    """Fetches jobs from public Greenhouse boards."""

    def __init__(self, board_token: str, company_name: str | None = None) -> None:
        self.board_token = board_token
        self._company_name = company_name or board_token.capitalize()

    @property
    def source_name(self) -> str:
        return "greenhouse"

    async def fetch(self, since: datetime | None = None) -> list[RawJob]:
        """Fetch all postings with full job content."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs?content=true"
        raw_jobs: list[RawJob] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(
                        "Greenhouse board %s returned status %d",
                        self.board_token,
                        resp.status_code,
                    )
                    return []

                data = resp.json()
                items: list[dict[str, Any]] = data.get("jobs", [])

                for item in items:
                    job_id = str(item.get("id", ""))
                    title = item.get("title", "")
                    location = item.get("location", {}).get("name", "")
                    app_url = item.get("absolute_url", "")
                    content = item.get("content", "")
                    updated_at_str = item.get("updated_at")

                    posted_at = None
                    if updated_at_str:
                        with contextlib.suppress(Exception):
                            posted_at = datetime.fromisoformat(
                                updated_at_str.replace("Z", "+00:00")
                            )

                    raw_jobs.append(
                        RawJob(
                            source=self.source_name,
                            external_id=job_id,
                            company_name=self._company_name,
                            title=title,
                            location_raw=location,
                            application_url=app_url,
                            description_raw=content,
                            posted_at=posted_at,
                            extra_data={"board_token": self.board_token},
                        )
                    )

        except Exception as e:
            logger.error("Error fetching Greenhouse board %s: %s", self.board_token, e)

        return raw_jobs

    def normalize(self, raw: RawJob) -> JobIn:
        """Convert Greenhouse RawJob to standardized JobIn."""
        # Unescape and clean HTML description
        desc_html = raw.description_raw or ""
        desc_unescaped = html.unescape(desc_html)
        # Some boards escape twice ("&amp;nbsp;"): unescape again after removing tags
        desc_text = html.unescape(re.sub(r"<[^>]+>", " ", desc_unescaped))
        desc_text = re.sub(r"\s+", " ", desc_text).strip()

        norm_title, seniority = extract_seniority(raw.title)
        locations = normalize_locations(raw.location_raw)
        remote_mode = detect_remote_mode(f"{raw.title} {raw.location_raw} {desc_text}")
        exp_min, exp_max = extract_experience_range(desc_text)
        sal_min, sal_max = extract_salary_lpa(desc_text)
        skills = extract_skills_from_text(desc_text)

        app_url = clean_url(raw.application_url)
        content_hash = compute_content_hash(
            company_name=raw.company_name,
            normalized_title=norm_title,
            primary_location=locations[0] if locations else "Bengaluru",
            application_url=app_url,
        )

        is_suspicious, quality_score = check_is_suspicious(
            title=raw.title,
            description=desc_text,
            company=raw.company_name,
            salary_max_lpa=sal_max,
        )

        return JobIn(
            source=self.source_name,
            external_id=raw.external_id,
            company_name=raw.company_name,
            title=raw.title,
            normalized_title=norm_title,
            seniority=seniority,
            location_raw=raw.location_raw,
            locations=locations,
            country="India",
            remote_mode=remote_mode,
            employment_type="full-time",
            description_html=desc_html,
            description_text=desc_text,
            salary_min_lpa=sal_min,
            salary_max_lpa=sal_max,
            salary_currency="INR",
            experience_min=exp_min,
            experience_max=exp_max,
            required_skills=skills,
            application_url=app_url,
            ats_type="greenhouse",
            posted_at=raw.posted_at,
            content_hash=content_hash,
            quality_score=quality_score,
            is_suspicious=is_suspicious,
        )
