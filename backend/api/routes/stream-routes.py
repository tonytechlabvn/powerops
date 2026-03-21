"""SSE streaming route.

GET /api/stream/{job_id}  — Server-Sent Events stream of real-time job output.

Supports Last-Event-ID header for transparent reconnect: the client resumes
from the line index it last received, replaying any missed output first.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Request
from sse_starlette.sse import EventSourceResponse

from backend.api.services.stream_service import stream_job_output
from backend.db.database import get_session
from backend.api.services.job_service import JobService
from backend.core.models import JobStatus

router = APIRouter(prefix="/api/stream", tags=["stream"])


@router.get("/{job_id}")
async def stream_job(
    job_id: str,
    request: Request,
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
) -> EventSourceResponse:
    """Stream real-time output for a job via Server-Sent Events.

    Reconnect support: pass Last-Event-ID header with the last received
    event index to replay missed lines on reconnect.
    """
    start_index = 0
    if last_event_id:
        try:
            start_index = int(last_event_id) + 1
        except ValueError:
            start_index = 0

    async def is_complete() -> bool:
        """Return True when job has reached a terminal state."""
        async with get_session() as session:
            svc = JobService(session)
            job = await svc.get_job(job_id)
        if job is None:
            return True
        return job.status in (
            JobStatus.completed,
            JobStatus.failed,
            JobStatus.cancelled,
        )

    async def event_generator():
        async for event in stream_job_output(
            job_id,
            last_event_id=start_index,
            is_complete_fn=is_complete,
        ):
            if await request.is_disconnected():
                break
            yield event

    return EventSourceResponse(event_generator())
