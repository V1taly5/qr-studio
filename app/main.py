from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.responses import Response
from app.core.config import settings
from app.core.logging import configure_logging
from app.exceptions import QRStudioError
from app.middleware.request_id import REQUEST_ID_HEADER, add_request_id


async def _max_content_length_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Reject requests whose Content-Length exceeds the configured limit."""
    content_length = request.headers.get("content-length")
    if content_length is not None and int(content_length) > settings.max_content_length:
        return JSONResponse(
            status_code=413,
            content={"success": False, "detail": "Request body too large"},
        )
    return await call_next(request)


def _error_response(request: Request, status_code: int, detail: str) -> JSONResponse:
    """Build a consistent error response, propagating the request ID when present."""
    headers: dict[str, str] = {}
    request_id = request.headers.get(REQUEST_ID_HEADER)
    if request_id:
        headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "detail": detail},
        headers=headers,
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title="QR Studio",
        version="1.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware
    app.middleware("http")(add_request_id)
    app.middleware("http")(_max_content_length_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(router)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    template_path = Path(__file__).resolve().parent / "templates" / "index.html"

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        """Serve the main web UI."""
        return template_path.read_text(encoding="utf-8")

    @app.exception_handler(QRStudioError)
    async def qr_studio_error_handler(request: Request, exc: QRStudioError) -> JSONResponse:
        """Return structured error responses for application exceptions."""
        return _error_response(request, status_code=400, detail=str(exc))

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler to prevent internal details from leaking."""
        import structlog

        logger = structlog.get_logger()
        logger.error("unhandled_exception", exc_info=exc, path=request.url.path)
        return _error_response(
            request,
            status_code=500,
            detail="Internal server error",
        )

    return app


app = create_app()


def main() -> None:
    """Run the application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers if not settings.reload else 1,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
