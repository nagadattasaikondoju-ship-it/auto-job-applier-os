"""Manual URL importer with ATS detection and JSON-LD fallback."""

import html
import json
import logging
import re
from urllib.parse import urlparse

import httpx

from packages.jobs_sources.base import JobIn, RawJob
from packages.jobs_sources.detector import detect_ats
from packages.jobs_sources.greenhouse import GreenhouseBoardConnector
from packages.jobs_sources.lever import LeverPostingsConnector
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

logger = logging.getLogger("applyon.jobs.manual")


class ManualUrlImporter:
    """Imports and normalizes a single job from any valid URL."""

    async def import_url(self, url: str, optional_text: str = "") -> JobIn:
        """Fetch, detect ATS, and extract full structured job details."""
        ats_type = detect_ats(url)
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        # 1. Greenhouse dedicated single-job API
        if ats_type == "greenhouse" and len(path_parts) >= 3 and path_parts[-2] == "jobs":
            board_token = path_parts[0] if path_parts[0] != "embed" else path_parts[1]
            job_id = path_parts[-1]
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(api_url)
                    if resp.status_code == 200:
                        connector = GreenhouseBoardConnector(board_token=board_token)
                        item = resp.json()
                        raw = RawJob(
                            source="greenhouse",
                            external_id=str(item.get("id", job_id)),
                            company_name=board_token.capitalize(),
                            title=item.get("title", "Software Engineer"),
                            location_raw=item.get("location", {}).get("name", "Bengaluru"),
                            application_url=url,
                            description_raw=item.get("content", ""),
                        )
                        return connector.normalize(raw)
            except Exception as e:
                logger.debug("Greenhouse direct job fetch failed, falling back to crawler: %s", e)

        # 2. Lever dedicated single-job API
        if ats_type == "lever" and len(path_parts) >= 2:
            company_id = path_parts[0]
            job_id = path_parts[1]
            api_url = f"https://api.lever.co/v0/postings/{company_id}/{job_id}"
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(api_url)
                    if resp.status_code == 200:
                        lever_connector = LeverPostingsConnector(company_id=company_id)
                        item = resp.json()
                        raw_job = RawJob(
                            source="lever",
                            external_id=str(item.get("id", job_id)),
                            company_name=company_id.capitalize(),
                            title=item.get("text", "Software Engineer"),
                            location_raw=item.get("categories", {}).get("location", "Bengaluru"),
                            application_url=item.get("hostedUrl", url),
                            description_raw=item.get("description", ""),
                        )
                        return lever_connector.normalize(raw_job)
            except Exception as e:
                logger.debug("Lever direct job fetch failed, falling back to crawler: %s", e)

        # 3. Generic HTML / JSON-LD extraction
        title = "Job Opportunity"
        company = parsed.hostname.split(".")[-2].capitalize() if parsed.hostname else "Company"
        location_raw = "Bengaluru, India"
        description_text = optional_text

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(
                timeout=25.0, headers=headers, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    html_content = resp.text

                    # Check for schema.org/JobPosting in JSON-LD
                    ld_matches = re.findall(
                        r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>',
                        html_content,
                        re.DOTALL | re.I,
                    )
                    for block in ld_matches:
                        try:
                            data = json.loads(block.strip())
                            if isinstance(data, list):
                                data = data[0] if data else {}
                            if data.get("@type") == "JobPosting":
                                title = data.get("title", title)
                                company = data.get("hiringOrganization", {}).get("name", company)
                                desc_raw = data.get("description", "")
                                if desc_raw:
                                    description_text = re.sub(
                                        r"<[^>]+>", " ", html.unescape(desc_raw)
                                    )
                                loc_data = data.get("jobLocation", {})
                                if isinstance(loc_data, dict):
                                    address = loc_data.get("address", {})
                                    if isinstance(address, dict):
                                        location_raw = address.get("addressLocality", location_raw)
                                break
                        except Exception:
                            continue

                    # Fallback to OG tags if JSON-LD wasn't present
                    if not description_text:
                        og_title = re.search(
                            r'<meta[^>]*property=[\'"]og:title[\'"][^>]*content=[\'"]([^\'"]+)[\'"]',
                            html_content,
                            re.I,
                        )
                        if og_title:
                            title = html.unescape(og_title.group(1))

                        og_desc = re.search(
                            r'<meta[^>]*property=[\'"]og:description[\'"][^>]*content=[\'"]([^\'"]+)[\'"]',
                            html_content,
                            re.I,
                        )
                        if og_desc:
                            description_text = html.unescape(og_desc.group(1))

                        if not description_text:
                            # Strip tags to get plain body text
                            body_match = re.search(
                                r"<body[^>]*>(.*?)</body>", html_content, re.DOTALL | re.I
                            )
                            raw_body = body_match.group(1) if body_match else html_content
                            cleaned_body = re.sub(
                                r"<script[^>]*>.*?</script>", " ", raw_body, flags=re.DOTALL | re.I
                            )
                            cleaned_body = re.sub(
                                r"<style[^>]*>.*?</style>",
                                " ",
                                cleaned_body,
                                flags=re.DOTALL | re.I,
                            )
                            description_text = re.sub(r"<[^>]+>", " ", cleaned_body)
                            description_text = re.sub(r"\s+", " ", description_text).strip()[:4000]

        except Exception as e:
            logger.warning("Error fetching manual URL %s: %s", url, e)

        if not description_text and optional_text:
            description_text = optional_text

        clean_app_url = clean_url(url)
        norm_title, seniority = extract_seniority(title)
        locations = normalize_locations(location_raw)
        remote_mode = detect_remote_mode(f"{title} {location_raw} {description_text}")
        exp_min, exp_max = extract_experience_range(description_text)
        sal_min, sal_max = extract_salary_lpa(description_text)
        skills = extract_skills_from_text(description_text)

        content_hash = compute_content_hash(
            company_name=company,
            normalized_title=norm_title,
            primary_location=locations[0] if locations else "Bengaluru",
            application_url=clean_app_url,
        )

        is_suspicious, quality_score = check_is_suspicious(
            title=title,
            description=description_text,
            company=company,
            salary_max_lpa=sal_max,
        )

        return JobIn(
            source="manual",
            external_id=content_hash[:16],
            company_name=company,
            title=title,
            normalized_title=norm_title,
            seniority=seniority,
            location_raw=location_raw,
            locations=locations,
            country="India",
            remote_mode=remote_mode,
            employment_type="full-time",
            description_html="",
            description_text=description_text,
            salary_min_lpa=sal_min,
            salary_max_lpa=sal_max,
            salary_currency="INR",
            experience_min=exp_min,
            experience_max=exp_max,
            required_skills=skills,
            application_url=clean_app_url,
            ats_type=ats_type,
            content_hash=content_hash,
            quality_score=quality_score,
            is_suspicious=is_suspicious,
        )
