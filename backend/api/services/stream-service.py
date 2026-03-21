"""SSE event buffer management.

Maintains an in-memory output buffer per job_id so SSE clients can replay
missed lines using Last-Event-ID and new clients can receive full history.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Global in-memory store: job_id -> list of buffered output lines
_output_buffers: dict[str, list[str]] = defaultdict(list)

# Per-job condition variables: woken when new lines are appended
_job_conditions: dict[str, asyncio.Condition] = {}

# Maximum lines kept in memory per job (older lines are dropped)
_MAX_BUFFER_LINES = 5000


def _get_condition(job_id: str) -> asyncio.Condition:
    """Return (creating if needed) the asyncio.Condition for a job."""
    if job_id not in _job_conditions:
        _job_conditions[job_id] = asyncio.Condition()
    return _job_conditions[job_id]


def append_line(job_id: str, line: str) -> None:
    """Append a line to the job's output buffer and wake waiting SSE clients.

    Safe to call from a BackgroundTask coroutine.
    """
    buf = _output_buffers[job_id]
    buf.append(line)
    # Trim oldest entries if buffer is too large
    if len(buf) > _MAX_BUFFER_LINES:
        _output_buffers[job_id] = buf[-_MAX_BUFFER_LINES:]

    cond = _get_condition(job_id)
    # Schedule notification on the running event loop
    try:
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_notify(cond)))
    except RuntimeError:
        pass  # No running loop — background task will notify on next iteration


async def _notify(cond: asyncio.Condition) -> None:
    async with cond:
        cond.notify_all()


def get_buffered_lines(job_id: str, after_index: int = 0) -> list[str]:
    """Return buffered lines for job starting from after_index."""
    return _output_buffers.get(job_id, [])[after_index:]


async def stream_job_output(
    job_id: str,
    last_event_id: int = 0,
    poll_timeout: float = 30.0,
    is_complete_fn=None,
) -> AsyncGenerator[dict, None]:
    """Async generator yielding SSE event dicts for a job's output.

    Yields buffered history first, then waits for new lines.
    Stops when is_complete_fn returns True and buffer is exhausted.

    Args:
        job_id: Target job identifier.
        last_event_id: Resume from this line index (for reconnect support).
        poll_timeout: Seconds to wait for new output before yielding keepalive.
        is_complete_fn: Optional async callable returning bool — when True and
                        buffer exhausted the stream ends.
    """
    index = last_event_id
    cond = _get_condition(job_id)

    while True:
        lines = get_buffered_lines(job_id, after_index=index)
        if lines:
            for i, line in enumerate(lines):
                event_id = index + i
                yield {"id": str(event_id), "event": "log", "data": line}
            index += len(lines)
        else:
            # Check if job is done and buffer exhausted
            if is_complete_fn and await is_complete_fn():
                yield {"event": "result", "data": "stream_complete"}
                return

            # Wait for new data or timeout (keepalive)
            try:
                async with cond:
                    await asyncio.wait_for(cond.wait(), timeout=poll_timeout)
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "keepalive"}


def clear_buffer(job_id: str) -> None:
    """Remove a job's buffer from memory (call after job completes)."""
    _output_buffers.pop(job_id, None)
    _job_conditions.pop(job_id, None)
    logger.debug("Cleared SSE buffer for job %s", job_id)
