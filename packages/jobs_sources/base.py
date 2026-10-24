"""Base classes and types for job sources and ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class RawJob:
    """Raw payload returned directly from a board or crawler."""

    source: str
    external_id: str
    company_name: str
    title: str
    location_raw: str
    application_url: str
    description_raw: str
    posted_at: datetime | None = None
    extra_data: dict[str, Any] = field(default_factory=dict)


class JobIn(BaseModel):
    """Normalized job schema ready for ingestion and deduplication."""

    source: str
    external_id: str
    company_name: str
    title: str
    normalized_title: str
    seniority: str = "fresher"  # intern | fresher | junior | mid | senior | lead
    location_raw: str = ""
    locations: list[str] = Field(default_factory=list)  # Canonical cities
    country: str = "India"
    remote_mode: str = "onsite"  # remote | hybrid | onsite
    employment_type: str = "full-time"
    description_html: str = ""
    description_text: str = ""
    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None
    salary_currency: str = "INR"
    experience_min: int = 0
    experience_max: int = 30
    required_skills: list[str] = Field(default_factory=list)
    application_url: str
    ats_type: str = "unknown"
    posted_at: datetime | None = None
    content_hash: str = ""
    quality_score: int = 100
    is_suspicious: bool = False


class BaseJobConnector(ABC):
    """Abstract interface for all job ingestion connectors."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the connector (e.g., 'greenhouse', 'lever', 'adzuna')."""
        ...

    @abstractmethod
    async def fetch(self, since: datetime | None = None) -> list[RawJob]:
        """Fetch raw jobs from the remote source."""
        ...

    @abstractmethod
    def normalize(self, raw: RawJob) -> JobIn:
        """Convert a raw job into our standardized JobIn schema."""
        ...
