#!/usr/bin/env python3
from __future__ import annotations

import uvicorn

from app.core.config import settings

"""Development entrypoint that enables auto-reload and reads settings from .env."""


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
