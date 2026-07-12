from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class GenerateRequest(BaseModel):
    """Request schema for QR code generation."""

    type: str = Field(
        ...,
        pattern=r"^(url|text)$",
        description="Type of input data: url or arbitrary text",
    )
    data: str = Field(..., min_length=1, description="Input data")
    format: str = Field(default="png", pattern=r"^(png|svg)$", description="Output format")

    @field_validator("data")
    @classmethod
    def _validate_data_length(cls, value: str) -> str:
        """Enforce the configured maximum content length on the data field."""
        if len(value) > settings.max_content_length:
            msg = f"Input data must not exceed {settings.max_content_length} characters"
            raise ValueError(msg)
        return value


class GenerateResponse(BaseModel):
    """Response schema for QR code generation."""

    success: bool = Field(..., description="Whether generation succeeded")
    format: str = Field(..., pattern=r"^(png|svg)$", description="Output format")
    data: str = Field(..., description="Base64 PNG or SVG markup")
