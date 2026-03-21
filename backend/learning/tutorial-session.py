"""TutorialSession — in-memory progress tracker for a single tutorial run.

Imported by tutorials.py via importlib because of the kebab-case filename.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


class TutorialSession:
    """Tracks a user's progress through a single tutorial.

    Stored in-memory inside TutorialEngine._sessions; no DB persistence.
    """

    def __init__(self, tutorial_name: str, total_steps: int) -> None:
        self.session_id: str = str(uuid.uuid4())
        self.tutorial_name: str = tutorial_name
        self.total_steps: int = total_steps
        self.current_step: int = 1
        self.completed_steps: list[int] = []
        self.started_at: str = datetime.now(timezone.utc).isoformat()
        self.completed_at: str | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """True when every step has been marked completed."""
        return len(self.completed_steps) >= self.total_steps

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable snapshot of the session."""
        return {
            "session_id": self.session_id,
            "tutorial_name": self.tutorial_name,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "is_complete": self.is_complete,
        }
