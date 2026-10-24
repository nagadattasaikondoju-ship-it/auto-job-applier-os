from typing import Literal

from pydantic import BaseModel, Field


class ParsedBullet(BaseModel):
    id: str = Field(..., description="Unique bullet identifier e.g. b1, b2")
    text: str = Field(..., description="Action-oriented bullet text with quantifiable impact")
    skills: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)


class ParsedExperience(BaseModel):
    company: str
    title: str
    employment_type: str = "full-time"
    location: str = ""
    start_date: str
    end_date: str | None = None
    is_current: bool = False
    bullets: list[ParsedBullet] = Field(default_factory=list)


class ParsedEducation(BaseModel):
    institution: str
    degree: str
    field: str = ""
    start_date: str = ""
    end_date: str = ""
    grade: str = ""
    board: str | None = None


class ParsedProject(BaseModel):
    title: str
    description: str
    role: str = ""
    url: str | None = None
    skills: list[str] = Field(default_factory=list)


class ParsedSkill(BaseModel):
    name: str
    normalized_name: str
    category: str = "technical"
    years: float = 1.0
    proficiency: str = "intermediate"


class ParsedResumeOutput(BaseModel):
    full_name: str
    email: str
    phone: str = ""
    city: str = ""
    state: str = ""
    country: str = "India"
    headline: str = ""
    summary: str = ""
    total_experience_months: int = 0
    current_title: str = ""
    current_company: str = ""
    experiences: list[ParsedExperience] = Field(default_factory=list)
    educations: list[ParsedEducation] = Field(default_factory=list)
    projects: list[ParsedProject] = Field(default_factory=list)
    skills: list[ParsedSkill] = Field(default_factory=list)


class MatchScoreOutput(BaseModel):
    job_id: str
    match_score: int = Field(..., ge=0, le=100)
    decision: Literal["apply", "maybe", "skip"]
    fit_reasons: list[str]
    gaps: list[str]
    resume_focus: list[str]
    risk_flags: list[str]


class TailoredBullet(BaseModel):
    source_bullet_id: str = Field(
        ..., description="Must reference an existing bullet ID from profile snapshot"
    )
    text: str = Field(
        ...,
        description="Tailored bullet text emphasizing relevant keywords without inventing facts",
    )


class TailoredExperience(BaseModel):
    experience_id: str
    company: str
    title: str
    bullets: list[TailoredBullet]


class TailoredResumeOutput(BaseModel):
    summary: str
    skills_ordered: list[str]
    experiences: list[TailoredExperience]
    keywords_used: list[str]
    changes_made: list[str]


class CoverLetterOutput(BaseModel):
    cover_letter_text: str = Field(
        ..., description="<= 300 words, company- and role-specific, facts only from profile"
    )
    word_count: int


class SingleScreeningAnswer(BaseModel):
    field_key: str
    question_text: str
    answer: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ScreeningAnswersOutput(BaseModel):
    answers: list[SingleScreeningAnswer]
