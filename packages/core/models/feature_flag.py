from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.models.base import Base, TimestampMixin


class FeatureFlag(Base, TimestampMixin):
    """System-wide feature flags and kill switches."""

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rules: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
