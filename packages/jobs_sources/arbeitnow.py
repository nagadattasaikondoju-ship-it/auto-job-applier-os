"""Arbeitnow job board connector using public job board API."""

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

logger = logging.getLogger("applyon.jobs.arbeitnow")


class ArbeitnowConnector(BaseJobConnector):
    """Fetches jobs from Arbeitnow public API."""

    @property
    def source_name(self) -> str:
        return "arbeitnow"

    async def fetch(self, since: datetime | None = None) -> list[RawJob]:
        """Fetch remote and tech postings from Arbeitnow."""
        url = "https://www.arbeitnow.com/api/job-board-api"
        raw_jobs: list[RawJob] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("Arbeitnow returned status %d", resp.status_code)
                    return []

                data = resp.json()
                items: list[dict[str, Any]] = data.get("data", [])

                for item in items:
                    job_id = str(item.get("slug", ""))
                    company = item.get("company_name", "Tech Co")
                    title = item.get("title", "")
                    location = item.get("location", "Remote")
                    app_url = item.get("url", "")
                    desc_html = item.get("description", "")
                    created_at_epoch = item.get("created_at")

                    posted_at = None
                    if created_at_epoch:
                        with contextlib.suppress(Exception):
                            posted_at = datetime.fromtimestamp(created_at_epoch)

                    is_remote = bool(item.get("remote", False))

                    raw_jobs.append(
                        RawJob(
                            source=self.source_name,
                            external_id=job_id,
                            company_name=company,
                            title=title,
                            location_raw="Remote" if is_remote else location,
                            application_url=app_url,
                            description_raw=desc_html,
                            posted_at=posted_at,
                            extra_data={"tags": item.get("tags", [])},
                        )
                    )

        except Exception as e:
            logger.error("Error fetching Arbeitnow jobs: %s", e)

        return raw_jobs

    def normalize(self, raw: RawJob) -> JobIn:
        """Convert Arbeitnow RawJob to standardized JobIn."""
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
            ats_type="unknown",
            posted_at=raw.posted_at,
            content_hash=content_hash,
            quality_score=quality_score,
            is_suspicious=is_suspicious,
        )
