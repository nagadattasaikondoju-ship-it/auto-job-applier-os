"""Job preferences: what the user wants, used for discovery, matching and auto-apply."""

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps.auth import AuthenticatedUser, get_current_user
from apps.api.deps.db import get_db
from packages.core.models.preferences import JobPreference
from packages.core.models.profile import Profile
from packages.core.services.jobs import assign_user_to_preference_buckets

router = APIRouter(prefix="/preferences", tags=["Preferences"])

Seniority = Literal["intern", "fresher", "junior", "mid", "senior", "lead"]
RemoteMode = Literal["remote", "hybrid", "onsite"]
ALL_REMOTE_MODES: tuple[RemoteMode, ...] = ("remote", "hybrid", "onsite")

# Experience window searched for each seniority level
EXPERIENCE_BANDS: dict[str, tuple[int, int]] = {
    "intern": (0, 1),
    "fresher": (0, 1),
    "junior": (1, 3),
    "mid": (3, 6),
    "senior": (5, 10),
    "lead": (8, 20),
}


class PreferencesPayload(BaseModel):
    target_roles: list[str] = Field(default_factory=list)  # trimmed to 10
    role_keywords: list[str] = Field(default_factory=list)  # trimmed to 30
    industries: list[str] = Field(default_factory=list)  # trimmed to 20
    seniority: Seniority = "fresher"
    locations: list[str] = Field(default_factory=list)  # trimmed to 15
    remote_mode: list[RemoteMode] = Field(default_factory=lambda: list(ALL_REMOTE_MODES))
    min_salary_lpa: float = Field(default=0, ge=0, le=500)
    company_size: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list, max_length=100)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=50)
    employment_types: list[str] = Field(default_factory=lambda: ["full-time"])
    visa_sponsorship_needed: bool = False
    daily_application_limit: int = Field(default=10, ge=1, le=60)
    min_match_score: int = Field(default=70, ge=0, le=100)
    apply_mode: Literal["review", "hybrid"] = "review"
    # Logistics shown in the same questionnaire, stored on the profile
    notice_period_days: int | None = Field(default=None, ge=0, le=365)
    current_ctc_lpa: float | None = Field(default=None, ge=0, le=500)
    expected_ctc_lpa: float | None = Field(default=None, ge=0, le=500)
    willing_to_relocate: bool | None = None

    @field_validator("min_salary_lpa", "current_ctc_lpa", "expected_ctc_lpa", mode="before")
    @classmethod
    def _rupees_to_lakhs(cls, v: Any) -> Any:
        """People often type CTC in rupees (600000) instead of lakhs (6): convert instead of rejecting."""
        try:
            amount = float(v)
        except (TypeError, ValueError):
            return v
        return round(amount / 100_000, 2) if amount >= 1_000 else v

    @field_validator(
        "target_roles", "role_keywords", "industries", "locations", "excluded_companies", "excluded_keywords",
        mode="before",
    )
    @classmethod
    def _dedupe_and_cap(cls, v: Any) -> Any:
        """Drop blanks and duplicates, and keep the first N items rather than failing the whole save."""
        if not isinstance(v, list):
            return v
        seen: set[str] = set()
        out: list[Any] = []
        for item in v:
            key = str(item).strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(str(item).strip())
        return out

    def model_post_init(self, __context: Any) -> None:
        caps = {"target_roles": 10, "role_keywords": 30, "industries": 20, "locations": 15}
        for name, cap in caps.items():
            setattr(self, name, getattr(self, name)[:cap])


def _to_dict(p: JobPreference | None, profile: Profile | None) -> dict[str, Any]:
    if p is None:
        return {"exists": False, **PreferencesPayload().model_dump(), **_logistics(profile)}
    return {
        "exists": True,
        "target_roles": p.target_roles,
        "role_keywords": p.role_keywords,
        "industries": p.industries,
        "seniority": p.seniority,
        "locations": p.locations,
        "remote_mode": p.remote_mode,
        "min_salary_lpa": p.min_salary_lpa,
        "company_size": p.company_size,
        "excluded_companies": p.excluded_companies,
        "excluded_keywords": p.excluded_keywords,
        "employment_types": p.employment_types,
        "visa_sponsorship_needed": p.visa_sponsorship_needed,
        "daily_application_limit": p.daily_application_limit,
        "min_match_score": p.min_match_score,
        "apply_mode": "hybrid" if p.auto_submit_enabled else "review",
        **_logistics(profile),
    }


def _logistics(profile: Profile | None) -> dict[str, Any]:
    return {
        "notice_period_days": profile.notice_period_days if profile else None,
        "current_ctc_lpa": profile.current_ctc_lpa if profile else None,
        "expected_ctc_lpa": profile.expected_ctc_lpa if profile else None,
        "willing_to_relocate": profile.willing_to_relocate if profile else None,
    }


@router.get("")
async def get_preferences(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user.user_id))).scalar_one_or_none()
    profile = (await db.execute(select(Profile).where(Profile.user_id == user.user_id))).scalar_one_or_none()
    return _to_dict(pref, profile)


@router.put("")
async def save_preferences(
    body: PreferencesPayload,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    pref = (await db.execute(select(JobPreference).where(JobPreference.user_id == user.user_id))).scalar_one_or_none()
    if pref is None:
        pref = JobPreference(user_id=user.user_id)
        db.add(pref)

    clean = lambda xs: [x.strip() for x in xs if x and x.strip()]  # noqa: E731
    pref.target_roles = clean(body.target_roles)
    pref.role_keywords = clean(body.role_keywords)
    pref.industries = clean(body.industries)
    pref.seniority = body.seniority
    pref.min_exp, pref.max_exp = EXPERIENCE_BANDS[body.seniority]
    pref.locations = clean(body.locations)
    pref.remote_mode = list(body.remote_mode) or ["remote", "hybrid", "onsite"]
    pref.min_salary_lpa = body.min_salary_lpa
    pref.company_size = clean(body.company_size)
    pref.excluded_companies = clean(body.excluded_companies)
    pref.excluded_keywords = clean(body.excluded_keywords)
    pref.employment_types = clean(body.employment_types) or ["full-time"]
    pref.visa_sponsorship_needed = body.visa_sponsorship_needed
    pref.daily_application_limit = body.daily_application_limit
    pref.min_match_score = body.min_match_score
    pref.auto_submit_enabled = body.apply_mode == "hybrid"

    profile = (await db.execute(select(Profile).where(Profile.user_id == user.user_id))).scalar_one_or_none()
    if profile is not None:
        for field in ("notice_period_days", "current_ctc_lpa", "expected_ctc_lpa", "willing_to_relocate"):
            value = getattr(body, field)
            if value is not None:
                setattr(profile, field, value)

    await assign_user_to_preference_buckets(
        session=db,
        user_id=user.user_id,
        roles=pref.target_roles,
        seniority=pref.seniority,
        locations=[c for c in pref.locations if c.lower() != "remote"],
        allows_remote="remote" in pref.remote_mode or any(c.lower() == "remote" for c in pref.locations),
    )
    await db.commit()
    return _to_dict(pref, profile)
