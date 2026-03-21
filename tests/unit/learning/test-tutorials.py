"""Unit tests for backend.learning.tutorials.TutorialEngine."""
from __future__ import annotations

import pytest

from backend.learning.tutorials import TutorialEngine


@pytest.fixture
def engine() -> TutorialEngine:
    """Fresh engine instance pointing at the real tutorials directory."""
    return TutorialEngine()


# ---------------------------------------------------------------------------
# list_tutorials
# ---------------------------------------------------------------------------


def test_list_tutorials_returns_5(engine: TutorialEngine) -> None:
    tutorials = engine.list_tutorials()
    assert len(tutorials) == 5


def test_list_tutorials_filter_aws_returns_3(engine: TutorialEngine) -> None:
    aws = engine.list_tutorials(provider="aws")
    assert len(aws) == 3
    assert all(t["provider"] == "aws" for t in aws)


def test_list_tutorials_filter_proxmox_returns_2(engine: TutorialEngine) -> None:
    proxmox = engine.list_tutorials(provider="proxmox")
    assert len(proxmox) == 2
    assert all(t["provider"] == "proxmox" for t in proxmox)


def test_list_tutorials_each_has_required_fields(engine: TutorialEngine) -> None:
    for t in engine.list_tutorials():
        assert "name" in t
        assert "title" in t
        assert "provider" in t
        assert "step_count" in t
        assert t["step_count"] > 0


# ---------------------------------------------------------------------------
# get_tutorial
# ---------------------------------------------------------------------------


def test_get_tutorial_returns_full_tutorial(engine: TutorialEngine) -> None:
    tutorial = engine.get_tutorial("your-first-ec2")
    assert tutorial["name"] == "your-first-ec2"
    assert "steps" in tutorial
    assert len(tutorial["steps"]) > 0


def test_get_tutorial_steps_have_id_and_title(engine: TutorialEngine) -> None:
    tutorial = engine.get_tutorial("your-first-ec2")
    for step in tutorial["steps"]:
        assert "id" in step
        assert "title" in step


def test_get_tutorial_raises_for_missing(engine: TutorialEngine) -> None:
    with pytest.raises(KeyError):
        engine.get_tutorial("non-existent-tutorial-xyz")


# ---------------------------------------------------------------------------
# start_tutorial / complete_step
# ---------------------------------------------------------------------------


def test_start_tutorial_creates_session(engine: TutorialEngine) -> None:
    session = engine.start_tutorial("your-first-ec2")
    assert session.tutorial_name == "your-first-ec2"
    assert session.current_step == 1
    assert session.completed_steps == []
    assert session.is_complete is False


def test_start_tutorial_session_stored(engine: TutorialEngine) -> None:
    session = engine.start_tutorial("your-first-ec2")
    state = engine.get_session(session.session_id)
    assert state["session_id"] == session.session_id
    assert state["tutorial_name"] == "your-first-ec2"


def test_complete_step_advances_progress(engine: TutorialEngine) -> None:
    session = engine.start_tutorial("your-first-ec2")
    result = engine.complete_step(session.session_id, 1)
    assert result["tutorial_complete"] is False
    assert 1 in engine._sessions[session.session_id].completed_steps
    assert engine._sessions[session.session_id].current_step == 2


def test_complete_all_steps_marks_complete(engine: TutorialEngine) -> None:
    session = engine.start_tutorial("your-first-ec2")
    tutorial = engine.get_tutorial("your-first-ec2")
    step_ids = [s["id"] for s in tutorial["steps"]]
    for step_id in step_ids:
        result = engine.complete_step(session.session_id, step_id)
    assert result["tutorial_complete"] is True
    assert result["next_step"] is None


def test_complete_step_invalid_session_raises(engine: TutorialEngine) -> None:
    with pytest.raises(KeyError):
        engine.complete_step("nonexistent-session-id", 1)
