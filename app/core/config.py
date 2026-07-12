from __future__ import annotations

import re

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}){1,2}$")
_RATE_LIMIT_RE = re.compile(
    r"^([1-9]\d*)\s*/\s*(s|sec|second|seconds|m|min|minute|minutes|h|hour|hours|d|day|days)$"
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QR_",
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8080, ge=1, le=65535, description="Server bind port")
    workers: int = Field(default=1, ge=1, description="Number of uvicorn workers")
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Request handling
    request_timeout: float = Field(default=10.0, gt=0.0, description="Request timeout in seconds")
    max_content_length: int = Field(
        default=2 * 1024,
        ge=1,
        description="Maximum request body size in bytes",
    )
    rate_limit: str = Field(default="10/minute", description="Rate limit per client")
    cors_origins: str = Field(
        default="",
        description="Comma-separated allowed CORS origins (empty means no cross-origin requests)",
    )

    # QR generation settings
    qr_fill_color: str = Field(default="#1e3a8a", description="QR module color")
    qr_back_color: str = Field(default="#ffffff", description="QR background color")
    qr_module_round: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Module corner radius as a fraction of module size",
    )
    qr_box_size: int = Field(default=12, ge=1, description="Size of each QR module in pixels")
    qr_border: int = Field(default=4, ge=0, description="QR border width in modules")

    @field_validator("rate_limit")
    @classmethod
    def _validate_rate_limit(cls, value: str) -> str:
        """Ensure rate limit follows '<count>/<unit>' format."""
        if not _RATE_LIMIT_RE.match(value):
            msg = "Rate limit must be in format '<count>/<unit>', e.g. '10/minute'"
            raise ValueError(msg)
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("qr_fill_color", "qr_back_color")
    @classmethod
    def _validate_hex_color(cls, value: str) -> str:
        """Ensure color is a valid 3 or 6 digit hex value."""
        if not _HEX_COLOR_RE.match(value):
            msg = f"Color must be a valid hex value like #1e3a8a, got {value!r}"
            raise ValueError(msg)
        return value


settings = Settings()
