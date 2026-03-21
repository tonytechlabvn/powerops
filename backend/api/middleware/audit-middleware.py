"""Request audit logging middleware.

Appends an AuditLog row for every mutating request (POST/PUT/DELETE/PATCH).
GET requests are skipped to avoid noise. Health checks are always skipped.
"""
from __future__ import annotations

import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.db.database import get_session
from backend.db.models import AuditLog

logger = logging.getLogger(__name__)

# Paths that should never be audited
_SKIP_PATHS = frozenset(["/api/health", "/docs", "/redoc", "/openapi.json"])
_AUDIT_METHODS = frozenset(["POST", "PUT", "DELETE", "PATCH"])


class AuditMiddleware(BaseHTTPMiddleware):
    """Log all mutating API requests as AuditLog rows in the database."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        path = request.url.path
        method = request.method

        if method in _AUDIT_METHODS and path not in _SKIP_PATHS:
            await self._write_audit(request, response, elapsed_ms)

        return response

    async def _write_audit(
        self, request: Request, response: Response, elapsed_ms: int
    ) -> None:
        """Persist audit record; failures are logged but never propagate."""
        try:
            details = {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "query": str(request.query_params),
            }
            action = f"{request.method.lower()}:{request.url.path}"
            user = request.headers.get("X-User", "anonymous")

            async with get_session() as session:
                log = AuditLog(
                    action=action[:64],
                    user=user[:128],
                    details_json=json.dumps(details),
                )
                session.add(log)
        except Exception as exc:
            logger.warning("Audit log write failed: %s", exc)
