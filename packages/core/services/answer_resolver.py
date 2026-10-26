"""Answer resolution engine matching profile, answer bank, and AI to application questions."""

import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.client import GeminiClient
from packages.core.models.jobs import Company, Job
from packages.core.models.matching import CoverLetter, ResumeVersion
from packages.core.models.preferences import AnswerBank, JobPreference
from packages.core.models.profile import Experience, Profile, Skill
from packages.core.seed.field_label_synonyms import normalize_field_label
from packages.core.services.form_schema import FieldDefinition


class ResolvedField(BaseModel):
    """An answer-resolved field ready for browser autofill or user review."""

    field_id: str
    label: str
    canonical_key: str | None = None
    field_type: str = "text"
    required: bool = False
    value: Any = None
    source: str = "unresolved"  # profile | answer_bank | ai | user
    confidence: float = 0.0
    needs_review: bool = True
    dom_selector: str | None = None
    options: list[str] = Field(default_factory=list)


class ResolvedPlan(BaseModel):
    """Complete set of resolved form inputs for a job application."""

    fields: list[ResolvedField]
    can_auto_submit: bool = False
    unresolved_count: int = 0


_IDENTITY_KEYS = {"first_name", "last_name", "full_name", "email", "phone", "resume", "resume_file", "cover_letter", "cover_letter_file"}
_YES_NO = re.compile(r"^(do|are|have|will|would|can|is|did|were)\s+you\b")
_STOP = {"the", "and", "with", "your", "our", "any", "prior", "previous", "relevant", "role", "roles", "field", "work"}


class ProfileFacts(BaseModel):
    """What rule-based answers may draw on."""

    model_config = {"arbitrary_types_allowed": True}
    profile: Any
    prefs: Any = None
    skills: list[str] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)


def is_yes_no(label: str) -> bool:
    return bool(_YES_NO.match(normalize_field_label(label)))


def dedupe_fields(fields: list[FieldDefinition]) -> list[FieldDefinition]:
    """Forms (Greenhouse especially) list name/email/phone/resume twice; keep the first of each."""
    seen: set[str] = set()
    out = []
    for f in fields:
        key = f.canonical_key if f.canonical_key in _IDENTITY_KEYS else f"label:{normalize_field_label(f.label)}"
        key = {"resume_file": "resume", "cover_letter_file": "cover_letter"}.get(key or "", key)
        if key in seen:
            continue
        seen.add(key or "")
        out.append(f)
    return out


def _lpa(value: float | None, field: FieldDefinition) -> Any:
    if value is None:
        return None
    return value if field.field_type == "number" else f"{value:g} LPA"


def rule_based_answer(field: FieldDefinition, facts: ProfileFacts) -> Any:
    """Exact answers from the profile for questions forms phrase in many ways. None = not handled."""
    norm = normalize_field_label(field.label)
    p = facts.profile
    if _YES_NO.match(norm):
        topic = re.search(r"experience (?:in|with|of|as|working (?:in|with|on))\s+(.+)", norm)
        if topic:
            known = " ".join([*facts.skills, *facts.titles, p.current_title or "", p.headline or ""]).lower()
            words = [w for w in re.findall(r"[a-z0-9+#.]+", topic.group(1)) if len(w) > 2 and w not in _STOP]
            # Compare word stems, so "analytics" matches "Data Analyst"
            return "Yes" if words and any(w[:5] in known for w in words) else None
        if re.search(r"authori[sz]ed to work in india|eligible to work in india|legally .*work in india", norm):
            return "Yes" if (p.work_authorization or {}).get("India", True) else None
        cities = [c.lower() for c in [*((facts.prefs.locations if facts.prefs else None) or []), p.city or ""] if c]
        cities += [{"bengaluru": "bangalore", "bangalore": "bengaluru", "gurugram": "gurgaon"}.get(c, c) for c in cities]
        if re.search(r"office|on.?site|relocat|commute|based (in|out of)", norm):
            modes = set((facts.prefs.remote_mode if facts.prefs else None) or [])
            office_ok = "onsite" in modes or ("hybrid" in modes and "5 days" not in norm and "five days" not in norm)
            if office_ok and any(c and c in norm for c in cities):
                return "Yes"
            if "relocat" in norm and p.willing_to_relocate:
                return "Yes"
        return None  # visas, other countries, relationships, legal: the user answers these
    days = p.notice_period_days
    if re.search(r"notice period|how soon can you (join|start)|when can you (join|start)|earliest (joining|start)|joining date|available to (join|start)", norm):
        if days is None:
            return None
        return days if field.field_type == "number" else ("Immediately" if days == 0 else f"{days} days")
    if re.search(r"\bectc\b|expected (ctc|salary|compensation|pay)|desired (salary|compensation|ctc|pay)|salary expectation", norm):
        return _lpa(p.expected_ctc_lpa, field)
    if re.search(r"\bctc\b|current (ctc|salary|compensation|pay)|present (ctc|salary)", norm):
        return _lpa(p.current_ctc_lpa, field)
    if re.search(r"where (do|are) you (currently )?(reside|live|based|located)|current (location|city)|where are you (currently )?based", norm):
        return ", ".join(x for x in [p.city, p.country] if x) or None
    if re.search(r"how did you (hear|find|learn|come across)", norm):
        return "Company careers page"
    return None


class AnswerResolutionService:
    """Resolves questions for an ATS form using profile, answer bank, and Gemini AI."""

    def __init__(self, db: AsyncSession, gemini_client: GeminiClient | None = None):
        self.db = db
        self.gemini = gemini_client or GeminiClient()

    async def resolve_fields(
        self,
        user_id: str,
        profile: Profile,
        job: Job,
        fields: list[FieldDefinition],
    ) -> ResolvedPlan:
        """Resolve values for all form fields with multi-tier fallback."""
        fields = dedupe_fields(fields)
        prefs = (
            await self.db.execute(select(JobPreference).where(JobPreference.user_id == user_id))
        ).scalar_one_or_none()
        skills = [s for s in (await self.db.execute(select(Skill.name).where(Skill.user_id == user_id))).scalars()]
        titles = [t for t in (await self.db.execute(select(Experience.title).where(Experience.user_id == user_id))).scalars()]
        has_cover_letter = (
            await self.db.execute(
                select(CoverLetter.id).where(CoverLetter.user_id == user_id, CoverLetter.job_id == job.id).limit(1)
            )
        ).scalar_one_or_none() is not None
        has_tailored_resume = (
            await self.db.execute(
                select(ResumeVersion.id)
                .where(ResumeVersion.user_id == user_id, ResumeVersion.job_id == job.id)
                .limit(1)
            )
        ).scalar_one_or_none() is not None
        facts = ProfileFacts(profile=profile, prefs=prefs, skills=skills, titles=titles)
        # 1. Fetch user's AnswerBank entries
        bank_stmt = select(AnswerBank).where(AnswerBank.user_id == user_id)
        bank_result = await self.db.execute(bank_stmt)
        bank_entries = list(bank_result.scalars().all())

        bank_by_key: dict[str, str] = {}
        bank_by_norm_text: dict[str, str] = {}
        for entry in bank_entries:
            if entry.question_key:
                bank_by_key[entry.question_key.lower()] = entry.answer_text
            bank_by_norm_text[normalize_field_label(entry.question_text)] = entry.answer_text

        # 2. Extract profile fields map
        parts = (profile.full_name or "").split()
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        links = profile.links or {}

        profile_map: dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone,
            "city": profile.city,
            "current_city": profile.city,
            "location": ", ".join(x for x in [profile.city, profile.country] if x) or None,
            "current_company": profile.current_company or None,
            "current_title": profile.current_title or None,
            "headline": profile.headline or None,
            "linkedin_url": links.get("linkedin") or links.get("LinkedIn"),
            "github_url": links.get("github") or links.get("GitHub"),
            "portfolio_url": links.get("portfolio") or links.get("Portfolio"),
            "notice_period_days": profile.notice_period_days,
            "current_ctc_lpa": profile.current_ctc_lpa,
            "expected_ctc_lpa": profile.expected_ctc_lpa,
            "total_experience_years": round((profile.total_experience_months or 0) / 12.0, 1),
            "work_authorization": "Yes" if (profile.work_authorization or {}).get("India", True) else "No",
            "resume": "Tailored resume (PDF)" if has_tailored_resume else "Your resume (PDF)",
            "resume_file": "Tailored resume (PDF)" if has_tailored_resume else "Your resume (PDF)",
            "cover_letter": "tailored_cover_letter.pdf" if has_cover_letter else None,
            "cover_letter_file": "tailored_cover_letter.pdf" if has_cover_letter else None,
        }

        resolved_list: list[ResolvedField] = []

        for field in fields:
            resolved_val: Any = None
            source = "unresolved"
            confidence = 0.0
            needs_review = False

            key = (field.canonical_key or "").lower()
            norm_label = normalize_field_label(field.label)

            rule_value = rule_based_answer(field, facts)

            # Step 1: Common questions answered from the profile by rule (CTC, notice, Yes/No, ...)
            if rule_value is not None:
                resolved_val = rule_value
                source = "profile"
                confidence = 0.95

            # Step 1b: Check master profile by canonical key
            elif key and key in profile_map and profile_map[key] is not None and not is_yes_no(field.label):
                val = profile_map[key]
                resolved_val = val if field.field_type == "number" else str(val)
                source = "profile"
                confidence = 1.0

            # Step 2: Check AnswerBank by canonical key
            elif key and key in bank_by_key:
                resolved_val = bank_by_key[key]
                source = "answer_bank"
                confidence = 0.95

            # Step 3: Check AnswerBank by normalized question text
            elif norm_label in bank_by_norm_text:
                resolved_val = bank_by_norm_text[norm_label]
                source = "answer_bank"
                confidence = 0.90

            # Step 4: For open-ended or company-specific questions, use Gemini AI
            # (never for Yes/No questions: visas, legal status and the like are the user's to answer)
            elif field.field_type in ("text", "textarea") and len(norm_label.split()) > 2 and not is_yes_no(field.label):
                try:
                    ai_answer = await self._generate_ai_answer(
                        profile=profile,
                        job=job,
                        question_label=field.label,
                    )
                    if ai_answer:
                        resolved_val = ai_answer
                        source = "ai"
                        confidence = 0.82
                except Exception:
                    resolved_val = None
                    source = "unresolved"
                    confidence = 0.0

            # Step 5: Check options matching if select/radio
            if field.options and resolved_val is not None:
                matched_opt = self._match_best_option(str(resolved_val), field.options)
                if matched_opt:
                    resolved_val = matched_opt
                else:
                    confidence = max(0.0, confidence - 0.3)

            # Flag review if required and unresolved, or confidence < 0.70
            if resolved_val is None or (field.required and confidence < 0.70) or confidence < 0.80:
                needs_review = True

            resolved_list.append(
                ResolvedField(
                    field_id=field.field_id,
                    label=field.label,
                    canonical_key=field.canonical_key,
                    field_type=field.field_type,
                    required=field.required,
                    value=resolved_val,
                    source=source,
                    confidence=confidence,
                    needs_review=needs_review,
                    dom_selector=field.dom_selector,
                    options=field.options,
                )
            )

        unresolved_count = sum(1 for f in resolved_list if f.needs_review)
        can_auto_submit = unresolved_count == 0

        return ResolvedPlan(
            fields=resolved_list,
            can_auto_submit=can_auto_submit,
            unresolved_count=unresolved_count,
        )

    def _match_best_option(self, value: str, options: list[str]) -> str | None:
        """Find the best matching select/dropdown option."""
        val_lower = value.strip().lower()
        for opt in options:
            if opt.strip().lower() == val_lower:
                return opt
        for opt in options:
            if val_lower in opt.lower() or opt.lower() in val_lower:
                return opt
        return None

    async def _generate_ai_answer(
        self,
        profile: Profile,
        job: Job,
        question_label: str,
    ) -> str:
        """Ask Gemini for a truthful, concise response grounded strictly in candidate profile."""
        company_name = (
            await self.db.execute(select(Company.name).where(Company.id == job.company_id))
        ).scalar_one_or_none() or "the company"
        prompt = f"""You are drafting a job application response on behalf of a candidate.
Strict rule: Do not invent facts, tools, degrees, or employers. Ground your response entirely in the candidate's actual background.

Candidate profile:
Name: {profile.full_name}
Summary: {profile.summary}
Experience: {round((profile.total_experience_months or 0) / 12.0, 1)} years
City: {profile.city}

Job applying for:
Title: {job.title}
Company: {company_name}
Job Description: {(job.description_text or "")[:1000]}

Application Question:
"{question_label}"

Answer in the first person ("I"). If the question asks for a single fact, reply with just that fact.
Otherwise write 2 to 3 sentences. Don't repeat the candidate's whole background:"""

        response = await self.gemini.generate_text(prompt=prompt, temperature=0.2)
        return response.strip().strip('"')
