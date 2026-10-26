"""Answer resolution engine matching profile, answer bank, and AI to application questions."""

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.ai.client import GeminiClient
from packages.core.models.jobs import Company, Job
from packages.core.models.preferences import AnswerBank
from packages.core.models.profile import Profile
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
            "resume": "master_resume.pdf",
            "resume_file": "master_resume.pdf",
            "cover_letter": "tailored_cover_letter.pdf",
        }

        resolved_list: list[ResolvedField] = []

        for field in fields:
            resolved_val: Any = None
            source = "unresolved"
            confidence = 0.0
            needs_review = False

            key = (field.canonical_key or "").lower()
            norm_label = normalize_field_label(field.label)

            # Step 1: Check master profile
            if key and key in profile_map and profile_map[key] is not None:
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
            elif field.field_type in ("text", "textarea") and len(norm_label.split()) > 2:
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

Provide a professional, 2 to 3 sentence answer written in the first person ("I"):"""

        response = await self.gemini.generate_text(prompt=prompt, temperature=0.2)
        return response.strip().strip('"')
