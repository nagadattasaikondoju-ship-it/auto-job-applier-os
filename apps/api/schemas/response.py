from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Any = Field(default=None, description="Additional context or validation details")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SuccessResponse[T](BaseModel):
    data: T
    message: str | None = None
