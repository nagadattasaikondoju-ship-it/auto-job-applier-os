"""Adzuna job search API connector for India."""

import contextlib
import html
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from packages.core.config import settings
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

logger = logging.getLogger("applyon.jobs.adzuna")


class AdzunaConnector(BaseJobConnector):
    """Fetches jobs from Adzuna Jobs API for India."""

    def __init__(
        self,
        keywords: str = "Software Engineer",
        city: str = "Bengaluru",
        country: str = "in",
    ) -> None:
        self.keywords = keywords
        self.city = city
        self.country = country

    @property
    def source_name(self) -> str:
        return "adzuna"

    async def fetch(self, since: datetime | None = None) -> list[RawJob]:
        """Fetch matching listings from Adzuna API."""
        app_id = settings.adzuna_app_id
        app_key = settings.adzuna_app_key

        if not app_id or not app_key:
            logger.info("Adzuna API credentials not configured; skipping remote fetch.")
            return []

        url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
        params: dict[str, str | int] = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 50,
            "what": self.keywords,
            "where": self.city,
            "content-type": "application/json",
        }
        raw_jobs: list[RawJob] = []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning("Adzuna API returned status %d", resp.status_code)
                    return []

                data = resp.json()
                results: list[dict[str, Any]] = data.get("results", [])

                for item in results:
                    job_id = str(item.get("id", ""))
                    company = item.get("company", {}).get("display_name", "Tech Employer")
                    title = item.get("title", "")
                    location = item.get("location", {}).get("display_name", self.city)
                    redirect_url = item.get("redirect_url", "")
                    description = item.get("description", "")
                    created_str = item.get("created")

                    posted_at = None
                    if created_str:
                        with contextlib.suppress(Exception):
                            posted_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))

                    sal_min_raw = item.get("salary_min")
                    sal_max_raw = item.get("salary_max")

                    raw_jobs.append(
                        RawJob(
                            source=self.source_name,
                            external_id=job_id,
                            company_name=company,
                            title=title,
                            location_raw=location,
                            application_url=redirect_url,
                            description_raw=description,
                            posted_at=posted_at,
                            extra_data={
                                "salary_min": sal_min_raw,
                                "salary_max": sal_max_raw,
                            },
                        )
                    )

        except Exception as e:
            logger.error("Error fetching Adzuna jobs: %s", e)

        return raw_jobs

    def normalize(self, raw: RawJob) -> JobIn:
        """Convert Adzuna RawJob to standardized JobIn."""
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
        # Check if Adzuna provided numbers
        if sal_min is None and raw.extra_data.get("salary_min"):
            raw_min = float(raw.extra_data["salary_min"])
            raw_max = float(raw.extra_data.get("salary_max", raw_min))
            if raw_min > 50_000:  # Annual INR
                sal_min = round(raw_min / 100_000, 2)
                sal_max = round(raw_max / 100_000, 2)

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
