"""Global exception handler middleware.

Converts all TerrabotError subclasses and unhandled exceptions into
consistent ErrorResponse JSON so the frontend always gets a structured body.
"""
from __future__ import annotations

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.core.exceptions import (
    ConfigError,
    TemplateError,
    TerrabotError,
    TerraformError,
    ValidationError,
)
from backend.core.exceptions import TimeoutError as TerrabotTimeoutError

logger = logging.getLogger(__name__)


def _error_body(error: str, detail: str = "", code: str = "") -> dict:
    return {"error": error, "detail": detail, "code": code}


async def terrabot_exception_handler(request: Request, exc: TerrabotError) -> JSONResponse:
    """Handle all TerrabotError subclasses with appropriate HTTP status codes."""
    if isinstance(exc, TerraformError):
        status = 422
        code = "TERRAFORM_ERROR"
        detail = exc.stderr or str(exc)
    elif isinstance(exc, ValidationError):
        status = 400
        code = "VALIDATION_ERROR"
        detail = "; ".join(exc.violations) if exc.violations else str(exc)
    elif isinstance(exc, TemplateError):
        status = 404
        code = "TEMPLATE_NOT_FOUND"
        detail = str(exc)
    elif isinstance(exc, ConfigError):
        status = 500
        code = "CONFIG_ERROR"
        detail = str(exc)
    elif isinstance(exc, TerrabotTimeoutError):
        status = 504
        code = "TIMEOUT"
        detail = str(exc)
    else:
        status = 500
        code = "INTERNAL_ERROR"
        detail = str(exc)

    logger.warning("TerrabotError [%s]: %s", code, exc.message, extra=exc.context)
    return JSONResponse(
        status_code=status,
        content=_error_body(exc.message, detail=detail, code=code),
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError (e.g. job/approval not found) as 404."""
    logger.debug("ValueError: %s", exc)
    return JSONResponse(
        status_code=404,
        content=_error_body(str(exc), code="NOT_FOUND"),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected exceptions — returns 500."""
    logger.error("Unhandled exception on %s %s", request.method, request.url.path)
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=_error_body(
            "An unexpected error occurred.",
            detail=type(exc).__name__,
            code="INTERNAL_ERROR",
        ),
    )
