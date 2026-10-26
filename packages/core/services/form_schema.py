"""Form schema extraction, question normalization, and caching per job."""

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models.jobs import Company, Job, JobFormSchema
from packages.core.seed.field_label_synonyms import lookup_canonical_field, normalize_field_label


class FieldDefinition(BaseModel):
    """Normalized definition of a single form input field in an ATS application."""

    field_id: str
    label: str
    canonical_key: str | None = None
    field_type: str = "text"  # text, textarea, email, tel, file, select, radio, checkbox, number
    required: bool = False
    options: list[str] = Field(default_factory=list)
    dom_selector: str | None = None


def infer_field_type_and_key(label: str, raw_type: str | None = None) -> tuple[str, str | None]:
    """Infer field type and canonical key from field label and raw type hints."""
    canonical = lookup_canonical_field(label)
    norm_label = normalize_field_label(label)

    # Type inference
    ftype = "text"
    raw_l = (raw_type or "").lower()
    if "file" in raw_l or "resume" in norm_label or "cv" in norm_label or "attachment" in norm_label:
        ftype = "file"
    elif "textarea" in raw_l or "describe" in norm_label or "tell us" in norm_label or "why" in norm_label:
        ftype = "textarea"
    elif "select" in raw_l or "choice" in raw_l or "dropdown" in raw_l:
        ftype = "select"
    elif "checkbox" in raw_l:
        ftype = "checkbox"
    elif "radio" in raw_l:
        ftype = "radio"
    elif "email" in raw_l or "email" in norm_label:
        ftype = "email"
    elif "phone" in raw_l or "tel" in raw_l or "mobile" in norm_label or "contact" in norm_label:
        ftype = "tel"
    elif "number" in raw_l or "ctc" in norm_label or "years" in norm_label or "cgpa" in norm_label or "notice" in norm_label or "days" in norm_label:
        ftype = "number"

    # Fallback canonical key heuristic if not directly matched in seed
    if not canonical:
        if "first name" in norm_label:
            canonical = "first_name"
        elif "last name" in norm_label:
            canonical = "last_name"
        elif "full name" in norm_label or norm_label == "name":
            canonical = "full_name"
        elif "email" in norm_label:
            canonical = "email"
        elif "phone" in norm_label or "mobile" in norm_label:
            canonical = "phone"
        elif "resume" in norm_label or "cv" in norm_label:
            canonical = "resume"
        elif "cover letter" in norm_label:
            canonical = "cover_letter"
        elif "linkedin" in norm_label:
            canonical = "linkedin_url"
        elif "github" in norm_label:
            canonical = "github_url"
        elif "portfolio" in norm_label or "website" in norm_label:
            canonical = "portfolio_url"
        elif "notice" in norm_label:
            canonical = "notice_period_days"
        elif "current ctc" in norm_label:
            canonical = "current_ctc_lpa"
        elif "expected ctc" in norm_label:
            canonical = "expected_ctc_lpa"
        elif "experience" in norm_label and re.search(r"years|how many|total experience", norm_label):
            canonical = "total_experience_years"

    return ftype, canonical


class GreenhouseFormExtractor:
    """Extract form schema from Greenhouse public board API or HTML."""

    @classmethod
    def parse_api_payload(cls, data: dict[str, Any]) -> list[FieldDefinition]:
        fields: list[FieldDefinition] = [
            FieldDefinition(
                field_id="first_name",
                label="First Name",
                canonical_key="first_name",
                field_type="text",
                required=True,
                dom_selector="input#first_name",
            ),
            FieldDefinition(
                field_id="last_name",
                label="Last Name",
                canonical_key="last_name",
                field_type="text",
                required=True,
                dom_selector="input#last_name",
            ),
            FieldDefinition(
                field_id="email",
                label="Email",
                canonical_key="email",
                field_type="email",
                required=True,
                dom_selector="input#email",
            ),
            FieldDefinition(
                field_id="phone",
                label="Phone",
                canonical_key="phone",
                field_type="tel",
                required=False,
                dom_selector="input#phone",
            ),
            FieldDefinition(
                field_id="resume",
                label="Resume / CV",
                canonical_key="resume",
                field_type="file",
                required=True,
                dom_selector="input[type='file']#resume",
            ),
            FieldDefinition(
                field_id="cover_letter",
                label="Cover Letter",
                canonical_key="cover_letter",
                field_type="file",
                required=False,
                dom_selector="input[type='file']#cover_letter",
            ),
        ]

        # Greenhouse custom questions
        questions = data.get("questions") or []
        for q in questions:
            q_id = str(q.get("id", ""))
            label = q.get("label", "")
            required = bool(q.get("required", False))
            raw_fields = q.get("fields") or [{}]
            field_info = raw_fields[0] if raw_fields else {}
            raw_type = field_info.get("type", "input_text")

            options = []
            values = field_info.get("values") or []
            for v in values:
                if isinstance(v, dict):
                    options.append(str(v.get("label") or v.get("value", "")))
                else:
                    options.append(str(v))

            ftype, canonical = infer_field_type_and_key(label, raw_type)
            if options and ftype not in ("select", "radio", "checkbox"):
                ftype = "select"

            fields.append(
                FieldDefinition(
                    field_id=f"custom_question_{q_id}",
                    label=label,
                    canonical_key=canonical,
                    field_type=ftype,
                    required=required,
                    options=options,
                    dom_selector=f"#job_application_answers_attributes_{q_id}_value",
                )
            )

        return fields


class LeverFormExtractor:
    """Extract form schema from Lever posting API or schema."""

    @classmethod
    def parse_api_payload(cls, data: dict[str, Any]) -> list[FieldDefinition]:
        fields: list[FieldDefinition] = [
            FieldDefinition(
                field_id="name",
                label="Full Name",
                canonical_key="full_name",
                field_type="text",
                required=True,
                dom_selector="input[name='name']",
            ),
            FieldDefinition(
                field_id="email",
                label="Email",
                canonical_key="email",
                field_type="email",
                required=True,
                dom_selector="input[name='email']",
            ),
            FieldDefinition(
                field_id="phone",
                label="Phone",
                canonical_key="phone",
                field_type="tel",
                required=False,
                dom_selector="input[name='phone']",
            ),
            FieldDefinition(
                field_id="org",
                label="Current Company",
                canonical_key="current_company",
                field_type="text",
                required=False,
                dom_selector="input[name='org']",
            ),
            FieldDefinition(
                field_id="urls[LinkedIn]",
                label="LinkedIn URL",
                canonical_key="linkedin_url",
                field_type="text",
                required=False,
                dom_selector="input[name='urls[LinkedIn]']",
            ),
            FieldDefinition(
                field_id="urls[GitHub]",
                label="GitHub URL",
                canonical_key="github_url",
                field_type="text",
                required=False,
                dom_selector="input[name='urls[GitHub]']",
            ),
            FieldDefinition(
                field_id="urls[Portfolio]",
                label="Portfolio URL",
                canonical_key="portfolio_url",
                field_type="text",
                required=False,
                dom_selector="input[name='urls[Portfolio]']",
            ),
            FieldDefinition(
                field_id="resume",
                label="Resume",
                canonical_key="resume",
                field_type="file",
                required=True,
                dom_selector="input[type='file'][name='resume']",
            ),
        ]

        custom_questions = data.get("customQuestions") or []
        for i, q in enumerate(custom_questions):
            label = q.get("text", "")
            q_type = q.get("type", "text")
            options = [str(opt.get("text", opt)) for opt in q.get("options", [])]
            required = bool(q.get("required", False))

            ftype, canonical = infer_field_type_and_key(label, q_type)
            if options and ftype not in ("select", "radio", "checkbox"):
                ftype = "select"

            fields.append(
                FieldDefinition(
                    field_id=f"custom_question_{i}",
                    label=label,
                    canonical_key=canonical,
                    field_type=ftype,
                    required=required,
                    options=options,
                    dom_selector=f"textarea[name='cards[{i}][text]'], input[name='cards[{i}][value]']",
                )
            )

        return fields


class GenericFormExtractor:
    """Generic fallback form schema builder with common application fields."""

    @classmethod
    def default_schema(cls) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                field_id="full_name",
                label="Full Name",
                canonical_key="full_name",
                field_type="text",
                required=True,
                dom_selector="input[name*='name' i]",
            ),
            FieldDefinition(
                field_id="email",
                label="Email",
                canonical_key="email",
                field_type="email",
                required=True,
                dom_selector="input[type='email'], input[name*='email' i]",
            ),
            FieldDefinition(
                field_id="phone",
                label="Phone Number",
                canonical_key="phone",
                field_type="tel",
                required=True,
                dom_selector="input[type='tel'], input[name*='phone' i]",
            ),
            FieldDefinition(
                field_id="current_city",
                label="Current City",
                canonical_key="city",
                field_type="text",
                required=False,
                dom_selector="input[name*='city' i], input[name*='location' i]",
            ),
            FieldDefinition(
                field_id="resume",
                label="Resume",
                canonical_key="resume",
                field_type="file",
                required=True,
                dom_selector="input[type='file']",
            ),
            FieldDefinition(
                field_id="notice_period",
                label="Notice Period (Days)",
                canonical_key="notice_period_days",
                field_type="number",
                required=False,
                dom_selector="input[name*='notice' i]",
            ),
            FieldDefinition(
                field_id="current_ctc",
                label="Current CTC (in LPA)",
                canonical_key="current_ctc_lpa",
                field_type="number",
                required=False,
                dom_selector="input[name*='current_ctc' i]",
            ),
            FieldDefinition(
                field_id="expected_ctc",
                label="Expected CTC (in LPA)",
                canonical_key="expected_ctc_lpa",
                field_type="number",
                required=False,
                dom_selector="input[name*='expected_ctc' i]",
            ),
        ]


class FormSchemaService:
    """Service to load, extract, or cache ATS application schemas."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_extract_schema(self, job: Job) -> JobFormSchema:
        """Fetch cached JobFormSchema or extract and persist new schema."""
        # 1. Check existing in DB
        result = await self.db.execute(
            select(JobFormSchema).where(JobFormSchema.job_id == job.id)
        )
        existing = result.scalars().first()
        if existing:
            return existing

        # 2. Extract schema based on ATS type
        extracted_fields: list[FieldDefinition] = []
        extraction_method = "generic"

        # Board token + posting id: from the URL when possible, else from the company registry
        company = (await self.db.execute(select(Company).where(Company.id == job.company_id))).scalar_one_or_none()
        registry_token = company.ats_board_token if company else None

        if job.ats_type == "greenhouse":
            m = re.search(r"greenhouse\.io/(?:embed/)?(?:jobs|v1/boards/)?([^/]+)/jobs/(\d+)", job.application_url)
            ids = (m.group(1), m.group(2)) if m else ((registry_token, job.external_id) if registry_token else None)
            if ids:
                board_token, ext_id = ids
                api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{ext_id}?questions=true"
                try:
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        resp = await client.get(api_url)
                        if resp.status_code == 200:
                            data = resp.json()
                            extracted_fields = GreenhouseFormExtractor.parse_api_payload(data)
                            extraction_method = "api"
                except Exception:
                    pass

        elif job.ats_type == "lever":
            m = re.search(r"jobs\.lever\.co/([^/]+)/([a-f0-9\-]+)", job.application_url)
            ids = (m.group(1), m.group(2)) if m else ((registry_token, job.external_id) if registry_token else None)
            if ids:
                lever_company, post_id = ids
                api_url = f"https://api.lever.co/v0/postings/{lever_company}/{post_id}"
                try:
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        resp = await client.get(api_url)
                        if resp.status_code == 200:
                            data = resp.json()
                            extracted_fields = LeverFormExtractor.parse_api_payload(data)
                            extraction_method = "api"
                except Exception:
                    pass

        # Fallback to generic schema if extraction didn't populate
        if not extracted_fields:
            if job.ats_type == "greenhouse":
                extracted_fields = GreenhouseFormExtractor.parse_api_payload({})
            elif job.ats_type == "lever":
                extracted_fields = LeverFormExtractor.parse_api_payload({})
            else:
                extracted_fields = GenericFormExtractor.default_schema()

        schema_json = [f.model_dump() for f in extracted_fields]

        form_schema = JobFormSchema(
            id=uuid.uuid4(),
            job_id=job.id,
            ats_type=job.ats_type or "generic",
            schema_json=schema_json,
            extraction_method=extraction_method,
            extracted_at=datetime.now(UTC),
            version=1,
            status="ready",
        )
        self.db.add(form_schema)
        await self.db.flush()
        return form_schema
