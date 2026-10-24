"""Deterministic matching rules: role/location/seniority filters and skill-overlap scoring.

These run before (and instead of, when AI is unavailable) the Gemini scoring stage, so every
user gets relevant jobs ranked sensibly even without AI.
"""

import re
from datetime import UTC, datetime
from typing import Any

# Words that don't identify a role on their own
_GENERIC = {
    "engineer", "engineering", "developer", "development", "senior", "junior", "lead", "manager",
    "associate", "specialist", "executive", "intern", "trainee", "staff", "principal", "sr", "jr",
    "i", "ii", "iii", "and", "of", "the", "/", "-", "&",
}

# Role term -> extra title phrases that mean the same job
_SYNONYMS: dict[str, list[str]] = {
    "frontend": ["front end", "front-end", "ui engineer", "ui developer", "react", "web developer"],
    "backend": ["back end", "back-end", "server", "api engineer"],
    "full stack": ["fullstack", "full-stack"],
    "software": ["sde", "software development engineer", "swe", "programmer"],
    "data scientist": ["machine learning", "ml scientist"],
    "ai / ml": ["machine learning", "ml engineer", "ai engineer", "applied scientist"],
    "ml": ["machine learning"],
    "devops": ["sre", "site reliability", "platform engineer", "infrastructure"],
    "qa": ["quality", "test", "sdet", "automation"],
    "product manager": ["product owner", "apm"],
    "ui/ux": ["product designer", "ux designer", "ui designer"],
    "data analyst": ["business analyst", "analytics", "bi analyst"],
    "digital marketing": ["growth marketing", "performance marketing", "seo"],
}

CITY_ALIASES: dict[str, list[str]] = {
    "bengaluru": ["bengaluru", "bangalore"],
    "bangalore": ["bengaluru", "bangalore"],
    "gurugram": ["gurugram", "gurgaon"],
    "gurgaon": ["gurugram", "gurgaon"],
    "delhi ncr": ["delhi", "gurugram", "gurgaon", "noida", "ncr", "faridabad", "ghaziabad"],
    "delhi": ["delhi", "new delhi"],
    "mumbai": ["mumbai", "bombay", "navi mumbai", "thane"],
    "chennai": ["chennai", "madras"],
    "kolkata": ["kolkata", "calcutta"],
}

_SENIOR_TITLE = re.compile(r"\b(senior|sr\.?|lead|principal|staff|head|director|vp|vice president|architect|manager)\b", re.I)
_INTERN_TITLE = re.compile(r"\b(intern|internship|trainee|apprentice)\b", re.I)


def role_title_patterns(target_roles: list[str], role_keywords: list[str] | None = None) -> list[str]:
    """SQL ILIKE patterns that a job title must match (any of them)."""
    patterns: set[str] = set()
    for role in [*target_roles, *(role_keywords or [])]:
        r = role.lower().strip()
        if not r:
            continue
        core = [w for w in re.split(r"[\s/,()]+", r) if w and w not in _GENERIC]
        phrase = " ".join(core)
        if phrase:
            patterns.add(phrase)
        for key, extras in _SYNONYMS.items():
            if key in r:
                patterns.update(extras)
        if not core:
            patterns.add(r)
    return [f"%{p}%" for p in sorted(patterns)]


def location_patterns(locations: list[str]) -> list[str]:
    pats: set[str] = set()
    for loc in locations:
        key = loc.lower().strip()
        if not key or key == "remote":
            continue
        for alias in CITY_ALIASES.get(key, [key]):
            pats.add(f"%{alias}%")
    return sorted(pats)


def seniority_excludes(seniority: str) -> tuple[bool, bool]:
    """(exclude senior/lead titles, exclude intern titles) for a user's level."""
    if seniority in ("intern", "fresher", "junior"):
        return True, seniority not in ("intern", "fresher")
    return False, True


def title_allowed(title: str, seniority: str) -> bool:
    no_senior, no_intern = seniority_excludes(seniority)
    if no_senior and _SENIOR_TITLE.search(title):
        return False
    return not (no_intern and _INTERN_TITLE.search(title))


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip().lower()
    if v in ("present", "current", "now"):
        return datetime.now(UTC)
    m = re.match(r"(\d{4})-(\d{1,2})", v)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=UTC)
    m = re.match(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", v)
    if m and m.group(1) in _MONTHS:
        return datetime(int(m.group(2)), _MONTHS[m.group(1)], 1, tzinfo=UTC)
    m = re.search(r"(\d{4})", v)
    return datetime(int(m.group(1)), 6, 1, tzinfo=UTC) if m else None


def estimate_experience_years(experiences: list[Any]) -> float:
    """Total years from experience start/end dates (overlaps not merged; good enough for filtering)."""
    total_days = 0
    for e in experiences:
        start = _parse_date(getattr(e, "start_date", None))
        end = datetime.now(UTC) if getattr(e, "is_current", False) else _parse_date(getattr(e, "end_date", None))
        if start and end and end > start:
            total_days += (end - start).days
    return round(total_days / 365.0, 1)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", s.lower())


def skill_overlap(user_skills: list[str], job: Any) -> tuple[list[str], list[str]]:
    """(matched user skills found in the job, job's required skills the user lacks)."""
    text = f"{job.title} {' '.join(job.required_skills or [])} {job.description_text or ''}".lower()
    matched = [s for s in user_skills if s and re.search(rf"(?<![\w]){re.escape(s.lower())}(?![\w])", text)]
    have = {_norm(s) for s in user_skills}
    missing = [s for s in (job.required_skills or []) if _norm(s) not in have]
    return matched, missing


def rule_based_score(
    user_skills: list[str],
    target_roles: list[str],
    job: Any,
    min_match_score: int,
) -> dict[str, Any]:
    """0–100 score from title fit and skill overlap, with plain-language reasons."""
    matched, missing = skill_overlap(user_skills, job)
    title_hit = any(
        re.search(p.strip("%").replace("%", ".*"), job.title.lower()) for p in role_title_patterns(target_roles)
    )
    skill_part = min(1.0, len(matched) / 6.0)
    required = job.required_skills or []
    coverage = (len(required) - len(missing)) / len(required) if required else skill_part
    score = round(100 * (0.40 * (1.0 if title_hit else 0.3) + 0.35 * skill_part + 0.25 * coverage))
    reasons = []
    if title_hit:
        reasons.append("Title matches the roles you're targeting")
    if matched:
        reasons.append(f"Uses your skills: {', '.join(matched[:5])}")
    decision = "apply" if score >= min_match_score else "maybe" if score >= min_match_score - 15 else "skip"
    return {
        "match_score": score,
        "decision": decision,
        "fit_reasons": reasons or ["Partial overlap with your profile"],
        "gaps": [f"{s} isn't in your profile" for s in missing[:4]],
        "resume_focus": matched[:3],
        "risk_flags": [],
    }
