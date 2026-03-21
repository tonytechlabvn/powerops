"""Low-level async subprocess execution utility.

Handles process creation, streaming stdout, stderr capture, and timeout
enforcement. Used exclusively by terraform-runner.py.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessResult:
    """Raw result from a subprocess execution."""

    __slots__ = ("return_code", "stdout", "stderr", "timed_out")

    def __init__(
        self,
        return_code: int,
        stdout: str,
        stderr: str,
        timed_out: bool = False,
    ):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        return self.return_code == 0 and not self.timed_out


async def run_process(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 1800,
) -> ProcessResult:
    """Run a subprocess, capture all output, enforce timeout.

    Args:
        args: Command + arguments list.
        cwd: Working directory for the process.
        env: Optional environment variables (merged with current env if None).
        timeout: Maximum seconds to wait before killing the process.

    Returns:
        ProcessResult with stdout, stderr, return code, and timeout flag.
    """
    logger.debug("exec %s in %s", args, cwd)

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()  # drain buffers after kill
            logger.warning("process timed out after %ds: %s", timeout, args[0])
            return ProcessResult(
                return_code=-1,
                stdout="",
                stderr=f"Process timed out after {timeout} seconds.",
                timed_out=True,
            )

        return ProcessResult(
            return_code=proc.returncode or 0,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
        )

    except FileNotFoundError:
        msg = f"Executable not found: {args[0]}"
        logger.error(msg)
        return ProcessResult(return_code=127, stdout="", stderr=msg)


async def stream_process(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 1800,
) -> AsyncGenerator[str, None]:
    """Stream stdout lines from a subprocess in real time.

    Yields each line as it arrives. Raises asyncio.TimeoutError if the
    total wall-clock time exceeds *timeout* seconds.

    Args:
        args: Command + arguments list.
        cwd: Working directory for the process.
        env: Optional environment variables.
        timeout: Maximum total seconds before cancellation.

    Yields:
        Decoded stdout lines (newline stripped).
    """
    logger.debug("stream %s in %s", args, cwd)

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd),
        env=env,
    )

    assert proc.stdout is not None  # guaranteed by PIPE

    deadline = asyncio.get_event_loop().time() + timeout

    try:
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                proc.kill()
                raise asyncio.TimeoutError()

            try:
                line_bytes = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=remaining
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise

            if not line_bytes:
                break  # EOF

            yield line_bytes.decode("utf-8", errors="replace").rstrip("\n")

    finally:
        # Ensure process is fully reaped to avoid zombies
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        await proc.wait()
