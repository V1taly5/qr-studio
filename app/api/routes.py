from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limit import create_rate_limit_dependency, get_memory_backend
from app.exceptions import InvalidInputError, QRStudioError
from app.middleware.request_id import REQUEST_ID_HEADER
from app.schemas.qr import GenerateRequest, GenerateResponse
from app.services.qr_service import QRStyle, StyledQRGenerator

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = structlog.get_logger()
router = APIRouter()
generator = StyledQRGenerator(
    QRStyle(
        fill_color=settings.qr_fill_color,
        back_color=settings.qr_back_color,
        module_round=settings.qr_module_round,
        box_size=settings.qr_box_size,
        border=settings.qr_border,
    )
)
rate_limit = create_rate_limit_dependency(get_memory_backend(settings.rate_limit))


_T = TypeVar("_T")


async def _run_with_timeout(coro: Awaitable[_T]) -> _T:
    """Run a coroutine with the configured request timeout."""
    return await asyncio.wait_for(coro, timeout=settings.request_timeout)


def _build_error_response(
    *,
    status_code: int,
    detail: str,
    request: Request | None = None,
) -> JSONResponse:
    """Build a consistent error response with request ID."""
    headers: dict[str, str] = {}
    if request is not None:
        request_id = request.headers.get(REQUEST_ID_HEADER)
        if request_id:
            headers[REQUEST_ID_HEADER] = request_id

    return JSONResponse(
        status_code=status_code,
        content={"success": False, "detail": detail},
        headers=headers,
    )


@router.get("/api/health")
async def health_check(request: Request) -> dict[str, str]:
    """Return service health status, including a smoke test of QR generation."""
    try:
        await _run_with_timeout(asyncio.to_thread(generator.generate_svg, "health-check"))
    except Exception as exc:  # pragma: no cover - defensive check
        logger.error("health_check_failed", exc_info=exc)
        raise HTTPException(
            status_code=503,
            detail="QR generation subsystem is unavailable",
        ) from exc

    return {"status": "ok", "service": "qr-studio"}


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(
    request: Request,
    req: GenerateRequest,
    _rate_limit: None = Depends(rate_limit),
) -> GenerateResponse:
    """Generate a QR code from the provided data."""
    logger.info("generate_request", qr_type=req.type, qr_format=req.format)

    try:
        data_str = _prepare_data(req)
    except InvalidInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        if req.format == "svg":
            result = await _run_with_timeout(asyncio.to_thread(generator.generate_svg, data_str))
            return GenerateResponse(success=True, format="svg", data=result)

        b64 = await _run_with_timeout(asyncio.to_thread(generator.generate_png, data_str))
        return GenerateResponse(
            success=True,
            format="png",
            data=f"data:image/png;base64,{b64}",
        )
    except TimeoutError as exc:
        logger.error("qr_generation_timeout", qr_type=req.type)
        raise HTTPException(
            status_code=504,
            detail="QR generation timed out",
        ) from exc
    except QRStudioError as exc:
        logger.error("qr_generation_failed", exc_info=exc, qr_type=req.type)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("unexpected_qr_generation_error", exc_info=exc, qr_type=req.type)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during QR generation",
        ) from exc


def _prepare_data(req: GenerateRequest) -> str:
    """Validate and normalize input data based on request type."""
    data_str = req.data.strip()
    if req.type == "text":
        return data_str

    if not data_str.startswith(("http://", "https://")):
        msg = "URL must start with http:// or https://"
        raise InvalidInputError(msg)
    return data_str
