"""Job normalization, deduplication, content hashing, and scam filtering."""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from packages.core.seed.city_aliases import normalize_city
from packages.core.seed.taxonomies import ALL_SKILLS

# Common seniority keywords
_SENIORITY_PATTERNS: list[tuple[str, str]] = [
    (r"\b(intern|internship|trainee|apprentice)\b", "intern"),
    (r"\b(fresher|entry[\s-]level|associate|graduate)\b", "fresher"),
    (r"\b(junior|jr\.?|level[\s-]1|l1)\b", "junior"),
    (r"\b(senior|sr\.?|lead|staff|principal|head|director|vp|manager)\b", "senior"),
    (r"\b(mid|experienced|level[\s-]2|l2)\b", "mid"),
]

# Scam indicators
_SCAM_KEYWORDS = [
    "registration fee",
    "security deposit",
    "pay to apply",
    "whatsapp only",
    "send cv to whatsapp",
    "direct joining without interview",
    "processing fee",
    "guaranteed job after payment",
    "100% placement fee",
]


def clean_url(url: str) -> str:
    """Strip tracking and UTM parameters from application URLs."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        # Keep non-tracking query parameters
        clean_params = [
            (k, v)
            for k, v in parse_qsl(parsed.query)
            if not k.startswith("utm_") and k not in ("ref", "fbclid", "gclid", "source", "gh_src")
        ]
        clean_query = urlencode(clean_params)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip("/"),
                parsed.params,
                clean_query,
                "",
            )
        )
    except Exception:
        return url.strip()


def extract_seniority(title: str) -> tuple[str, str]:
    """Extract seniority tier and return (clean_title, seniority)."""
    title_lower = title.lower()
    seniority = "mid"  # default mid-level if unspecified

    for pattern, tier in _SENIORITY_PATTERNS:
        if re.search(pattern, title_lower):
            seniority = tier
            break

    # Strip seniority words for normalized title
    cleaned = re.sub(
        r"\b(senior|sr\.?|junior|jr\.?|intern|internship|lead|staff|principal|fresher|entry[\s-]level)\b",
        "",
        title_lower,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or title_lower, seniority


def detect_remote_mode(text: str) -> str:
    """Classify remote mode: remote, hybrid, or onsite."""
    text_lower = text.lower()
    if (
        "remote" in text_lower
        or "work from home" in text_lower
        or "wfh" in text_lower
        or "anywhere" in text_lower
    ):
        return "remote"
    if "hybrid" in text_lower or "flexible" in text_lower:
        return "hybrid"
    return "onsite"


def normalize_locations(location_raw: str) -> list[str]:
    """Parse comma/slash separated locations into canonical Indian city names."""
    if not location_raw:
        return ["Bengaluru"]  # Default primary tech hub

    cities: list[str] = []
    # Split by common delimiters
    tokens = re.split(r"[,/|;+&]|\band\b", location_raw)
    for token in tokens:
        cleaned = token.strip()
        if not cleaned:
            continue
        canonical = normalize_city(cleaned)
        if canonical not in cities:
            cities.append(canonical)

    return cities or [normalize_city(location_raw)]


def extract_experience_range(text: str) -> tuple[int, int]:
    """Extract minimum and maximum experience in years."""
    # Look for patterns like "3-5 years", "2 to 4 yrs", "5+ years", "0-1 yr"
    match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)", text, re.I)
    if match:
        return int(match.group(1)), int(match.group(2))

    plus_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", text, re.I)
    if plus_match:
        val = int(plus_match.group(1))
        return val, val + 4

    if re.search(r"\b(fresher|intern|entry[\s-]level)\b", text, re.I):
        return 0, 1

    return 0, 30


def extract_salary_lpa(text: str) -> tuple[float | None, float | None]:
    """Extract minimum and maximum salary normalized to LPA (Lakhs Per Annum INR)."""
    # Pattern: 10 - 20 LPA, 15 LPA
    lpa_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lac|lakh)", text, re.I
    )
    if lpa_match:
        return float(lpa_match.group(1)), float(lpa_match.group(2))

    single_lpa = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lac|lakh)", text, re.I)
    if single_lpa:
        val = float(single_lpa.group(1))
        return val, val

    # Pattern: Annual numbers in INR (e.g. 800000 - 1200000)
    annual_match = re.search(r"₹?\s*(\d{5,8})\s*(?:-|to)\s*₹?\s*(\d{5,8})", text)
    if annual_match:
        low = round(float(annual_match.group(1)) / 100_000, 2)
        high = round(float(annual_match.group(2)) / 100_000, 2)
        if 1.0 <= low <= 300.0:
            return low, high

    return None, None


def extract_skills_from_text(text: str) -> list[str]:
    """Match skills against taxonomy in text."""
    text_lower = text.lower()
    matched = []
    for skill in ALL_SKILLS:
        # Match as whole word
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            matched.append(skill)
    return matched[:20]


def check_is_suspicious(
    title: str, description: str, company: str, salary_max_lpa: float | None
) -> tuple[bool, int]:
    """Detect scam or low-quality job postings. Returns (is_suspicious, quality_score)."""
    combined = f"{title} {description}".lower()
    score = 100

    # Scam keywords
    for keyword in _SCAM_KEYWORDS:
        if keyword in combined:
            return True, 0

    # Unrealistic salary check (e.g. fresher role paying > 150 LPA)
    if salary_max_lpa and salary_max_lpa > 150 and ("fresher" in combined or "intern" in combined):
        return True, 20

    # Missing basic requirements or too short
    if len(description.strip()) < 100:
        score -= 40

    if not company or company.lower() in ("unknown", "confidential", "hiring"):
        score -= 30

    return (score < 40), max(0, score)


def compute_content_hash(
    company_name: str,
    normalized_title: str,
    primary_location: str,
    application_url: str,
) -> str:
    """Generate deterministic unique SHA256 content hash."""
    clean_app_url = clean_url(application_url)
    raw = f"{company_name.lower().strip()}|{normalized_title.lower().strip()}|{primary_location.lower().strip()}|{clean_app_url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
