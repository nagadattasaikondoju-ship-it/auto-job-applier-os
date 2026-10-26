"""OpenWebNinja job search connectors.

- JSearch: Google for Jobs listings, which include LinkedIn, Naukri, Indeed and company career sites.
- Real-Time Jobs Data: the same Google for Jobs search plus Indeed and LinkedIn searched directly.

Both APIs return the same job fields, so one normalizer serves every endpoint.

When a listing can be applied to on a public Greenhouse, Lever or Ashby board, that link is
preferred (Applyon can auto-apply there) and the company's board token is recorded so the
whole board gets crawled from then on.
"""

import contextlib
import html
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from packages.core.config import settings
from packages.jobs_sources.base import BaseJobConnector, JobIn, RawJob
from packages.jobs_sources.detector import board_token_from_url
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

logger = logging.getLogger("applyon.jobs.jsearch")

# Boards Applyon can submit to, best first
_AUTO_APPLY_ATS = ("greenhouse", "lever", "ashby")

_EMPLOYMENT_TYPES = {
    "FULLTIME": "full-time",
    "PARTTIME": "part-time",
    "CONTRACTOR": "contract",
    "INTERN": "internship",
}

_COUNTRY_NAMES = {"IN": "India"}


def pick_apply_link(item: dict[str, Any]) -> tuple[str, str, str | None]:
    """Choose the apply link to store: an auto-appliable board first, then a direct link, then the default.

    Returns (url, ats_type, board_token).
    """
    options = [o for o in (item.get("apply_options") or []) if isinstance(o, dict) and o.get("apply_link")]
    candidates = [str(o["apply_link"]) for o in options]
    default = str(item.get("job_apply_link") or "")
    if default:
        candidates.append(default)

    detected = [(url, *board_token_from_url(url)) for url in candidates]
    for ats in _AUTO_APPLY_ATS:
        for url, kind, token in detected:
            if kind == ats and token:
                return url, kind, token
    for url, kind, token in detected:
        if kind != "unknown":
            return url, kind, token
    direct = next((str(o["apply_link"]) for o in options if o.get("is_direct")), "")
    url = direct or default or (candidates[0] if candidates else "")
    return url, "unknown", None


def _salary_lpa(item: dict[str, Any]) -> tuple[float | None, float | None]:
    """Convert JSearch salary numbers to lakhs per annum (INR listings only)."""
    low: Any = item.get("job_min_salary") or item.get("job_max_salary")
    high: Any = item.get("job_max_salary") or low
    if not low:
        return None, None
    if (item.get("job_country") or "").upper() != "IN":
        return None, None
    if (item.get("job_salary_currency") or "INR").upper() != "INR":
        return None, None
    period = (item.get("job_salary_period") or "YEAR").upper()
    factor = {"YEAR": 1, "MONTH": 12}.get(period)
    if factor is None:
        return None, None
    try:
        lo = float(low) * factor
        hi = float(high) * factor
    except (TypeError, ValueError):
        return None, None
    if lo < 50_000:  # not an annual INR figure
        return None, None
    return round(lo / 100_000, 2), round(hi / 100_000, 2)


class OpenWebNinjaJobsConnector(BaseJobConnector):
    """One search call against an OpenWebNinja jobs endpoint (x-api-key auth)."""

    def __init__(self, source: str, url: str, params: dict[str, str | int], api_key: str) -> None:
        self._source = source
        self.url = url
        self.params = params
        self.api_key = api_key

    @property
    def source_name(self) -> str:
        return self._source

    async def fetch(self, since: datetime | None = None) -> list[RawJob]:
        if not self.api_key:
            logger.info("%s API key not configured; skipping.", self._source)
            return []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(self.url, params=self.params, headers={"x-api-key": self.api_key})
        except Exception as e:
            logger.error("Error fetching %s jobs: %s", self._source, e)
            return []
        if resp.status_code != 200:
            logger.warning("%s returned status %d for %r", self._source, resp.status_code, self.params.get("query"))
            return []
        return [self.to_raw(item) for item in extract_items(resp.json()) if item.get("job_id")]

    def to_raw(self, item: dict[str, Any]) -> RawJob:
        posted_at = None
        if item.get("job_posted_at_datetime_utc"):
            with contextlib.suppress(Exception):
                posted_at = datetime.fromisoformat(str(item["job_posted_at_datetime_utc"]).replace("Z", "+00:00"))
        location = item.get("job_location") or ", ".join(
            str(p) for p in (item.get("job_city"), item.get("job_state"), item.get("job_country")) if p
        )
        url, ats, token = pick_apply_link(item)
        return RawJob(
            source=self.source_name,
            external_id=str(item["job_id"]),
            company_name=str(item.get("employer_name") or "Unknown employer"),
            title=str(item.get("job_title") or ""),
            location_raw=str(location or ""),
            application_url=url,
            description_raw=str(item.get("job_description") or ""),
            posted_at=posted_at,
            extra_data={
                "ats_type": ats,
                "board_token": token,
                "is_remote": bool(item.get("job_is_remote")),
                "employment_type": item.get("job_employment_type"),
                "country": item.get("job_country"),
                "salary": _salary_lpa(item),
            },
        )

    def normalize(self, raw: RawJob) -> JobIn:
        desc_raw = raw.description_raw or ""
        desc_text = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(desc_raw)))
        desc_text = re.sub(r"\s+", " ", desc_text).strip()

        norm_title, seniority = extract_seniority(raw.title)
        locations = normalize_locations(raw.location_raw)
        remote_mode = (
            "remote" if raw.extra_data.get("is_remote")
            else detect_remote_mode(f"{raw.title} {raw.location_raw}")
        )
        exp_min, exp_max = extract_experience_range(desc_text)
        sal_min, sal_max = extract_salary_lpa(desc_text)
        if sal_min is None:
            sal_min, sal_max = raw.extra_data.get("salary") or (None, None)

        app_url = clean_url(raw.application_url)
        is_suspicious, quality_score = check_is_suspicious(
            title=raw.title,
            description=desc_text,
            company=raw.company_name,
            salary_max_lpa=sal_max,
        )
        country_code = str(raw.extra_data.get("country") or "IN").upper()
        return JobIn(
            source=self.source_name,
            external_id=raw.external_id,
            company_name=raw.company_name,
            title=raw.title,
            normalized_title=norm_title,
            seniority=seniority,
            location_raw=raw.location_raw,
            locations=locations,
            country=_COUNTRY_NAMES.get(country_code, country_code),
            remote_mode=remote_mode,
            employment_type=_EMPLOYMENT_TYPES.get(str(raw.extra_data.get("employment_type") or "").upper(), "full-time"),
            description_html=desc_raw,
            description_text=desc_text,
            salary_min_lpa=sal_min,
            salary_max_lpa=sal_max,
            salary_currency="INR",
            experience_min=exp_min,
            experience_max=exp_max,
            required_skills=extract_skills_from_text(desc_text),
            application_url=app_url,
            ats_type=str(raw.extra_data.get("ats_type") or "unknown"),
            ats_board_token=raw.extra_data.get("board_token"),
            posted_at=raw.posted_at,
            content_hash=compute_content_hash(
                company_name=raw.company_name,
                normalized_title=norm_title,
                primary_location=locations[0] if locations else "Bengaluru",
                application_url=app_url,
            ),
            quality_score=quality_score,
            is_suspicious=is_suspicious,
        )


def extract_items(payload: Any) -> list[dict[str, Any]]:
    """JSearch returns {"data": [...]} (v1) or {"data": {"jobs": [...]}} (v2); accept both."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        data = data.get("jobs") or data.get("data") or []
    return [d for d in (data or []) if isinstance(d, dict)]


class JSearchConnector(OpenWebNinjaJobsConnector):
    """JSearch search-v2, e.g. query="Data Analyst jobs in Bengaluru"."""

    def __init__(self, query: str, country: str = "in", date_posted: str = "week", num_pages: int = 1) -> None:
        super().__init__(
            source="jsearch",
            url=f"{settings.jsearch_base_url.rstrip('/')}/search-v2",
            params={"query": query, "country": country, "date_posted": date_posted, "num_pages": num_pages},
            api_key=settings.jsearch_api_key,
        )
        self.query = query


# Real-Time Jobs Data endpoints Applyon can search, with how each wants role and city
REALTIME_SOURCES = ("google_jobs", "indeed", "linkedin")


def realtime_jobs_connector(source: str, role: str, city: str) -> OpenWebNinjaJobsConnector:
    """Build a Real-Time Jobs Data search for one role and city (city "India" means country-wide)."""
    base = settings.realtime_jobs_base_url.rstrip("/")
    whole_country = city.strip().lower() == "india"
    params: dict[str, str | int] = {"country": "in", "date_posted": "week"}
    if source == "google_jobs":
        path = "google-jobs/search"
        params["query"] = f"{role} jobs in {'India' if whole_country else city}"
    elif source == "indeed":
        path = "indeed/search"
        params["query"] = role
        if not whole_country:
            params["location"] = city
    elif source == "linkedin":
        path = "linkedin/search"
        params["query"] = role
        params["location"] = "India" if whole_country else f"{city}, India"
    else:
        raise ValueError(f"Unknown Real-Time Jobs Data source: {source}")
    return OpenWebNinjaJobsConnector(
        source=source,
        url=f"{base}/{path}",
        params=params,
        api_key=settings.realtime_jobs_api_key or settings.jsearch_api_key,
    )
