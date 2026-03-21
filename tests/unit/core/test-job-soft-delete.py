"""Unit tests for job soft-delete (is_hidden) feature."""
from __future__ import annotations

import pytest

from backend.core.models import Job, JobStatus, JobType


def test_job_is_hidden_defaults_false() -> None:
    job = Job(id="j1", type=JobType.plan)
    assert job.is_hidden is False


def test_job_is_hidden_can_be_set_true() -> None:
    job = Job(id="j1", type=JobType.apply, is_hidden=True)
    assert job.is_hidden is True


def test_job_is_hidden_round_trip() -> None:
    job = Job(id="j1", type=JobType.destroy, is_hidden=True)
    data = job.model_dump()
    assert data["is_hidden"] is True
    restored = Job(**data)
    assert restored.is_hidden is True


def test_job_is_hidden_in_terminal_statuses() -> None:
    """Verify is_hidden works with all terminal statuses."""
    for status in (JobStatus.completed, JobStatus.failed, JobStatus.cancelled):
        job = Job(id="j1", type=JobType.plan, status=status, is_hidden=True)
        assert job.is_hidden is True
        assert job.status == status


def test_job_is_hidden_preserved_in_serialisation() -> None:
    job = Job(id="j1", type=JobType.apply, status=JobStatus.completed, is_hidden=True)
    data = job.model_dump(mode="json")
    assert "is_hidden" in data
    assert data["is_hidden"] is True
