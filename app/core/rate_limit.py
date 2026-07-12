from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING, Protocol

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class RateLimitBackend(Protocol):
    """Backend contract for rate limiting."""

    def is_allowed(self, key: str) -> bool:
        """Return True if the request is within the rate limit."""
        ...


@dataclass
class MemoryRateLimitBackend:
    """Thread-safe in-memory sliding-window rate limiter."""

    max_requests: int
    window_seconds: int
    _requests: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list),
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def is_allowed(self, key: str) -> bool:
        """Check whether a request from the given key is allowed."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            window = [ts for ts in self._requests[key] if ts > cutoff]
            if len(window) >= self.max_requests:
                self._requests[key] = window
                return False

            window.append(now)
            self._requests[key] = window
            return True


def parse_rate_limit(rate_limit: str) -> tuple[int, int]:
    """Parse a rate limit string such as '10/minute' into (count, window_seconds)."""
    try:
        count_str, unit = rate_limit.split("/")
        count = int(count_str.strip())
        if count < 1:
            raise ValueError
        unit = unit.strip().lower()
    except ValueError as exc:
        msg = f"Invalid rate limit format: {rate_limit}"
        raise ValueError(msg) from exc

    unit_to_seconds = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
    }

    if unit not in unit_to_seconds:
        msg = f"Invalid rate limit unit: {unit}"
        raise ValueError(msg)

    return count, unit_to_seconds[unit]


@lru_cache(maxsize=16)
def get_memory_backend(rate_limit: str) -> MemoryRateLimitBackend:
    """Return a cached in-memory rate limit backend for the given spec."""
    max_requests, window_seconds = parse_rate_limit(rate_limit)
    return MemoryRateLimitBackend(max_requests=max_requests, window_seconds=window_seconds)


def create_rate_limit_dependency(
    backend: RateLimitBackend,
) -> Callable[[Request], Awaitable[None]]:
    """Create a FastAPI dependency that enforces the given rate limit backend."""

    async def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        if not backend.is_allowed(client_host):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return dependency
