"""Tutorial engine — loads YAML tutorials and manages in-memory sessions.

Tutorials live under backend/learning/tutorials/{provider}/*.yaml.
TutorialSession is defined in tutorial-session.py (loaded via importlib).
Sessions are stored in-process only — no DB required for MVP.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_TUTORIALS_DIR = Path(__file__).parent / "tutorials"

# ---------------------------------------------------------------------------
# Load TutorialSession from kebab-case module
# ---------------------------------------------------------------------------

_SESSION_MODULE_NAME = "backend.learning.tutorial_session"
_SESSION_MODULE_FILE = Path(__file__).parent / "tutorial-session.py"


def _load_session_module():
    if _SESSION_MODULE_NAME in sys.modules:
        return sys.modules[_SESSION_MODULE_NAME]
    spec = importlib.util.spec_from_file_location(_SESSION_MODULE_NAME, _SESSION_MODULE_FILE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate tutorial-session.py at {_SESSION_MODULE_FILE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_SESSION_MODULE_NAME] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


TutorialSession = _load_session_module().TutorialSession


# ---------------------------------------------------------------------------
# Tutorial engine
# ---------------------------------------------------------------------------


class TutorialEngine:
    """Loads tutorials from YAML and manages in-memory sessions."""

    def __init__(self, tutorials_dir: Path | None = None) -> None:
        self._dir = tutorials_dir or _TUTORIALS_DIR
        self._cache: dict[str, dict] = {}
        self._sessions: dict[str, Any] = {}  # session_id -> TutorialSession
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_tutorials(self, provider: str | None = None) -> list[dict]:
        """Return summary list of available tutorials, optionally filtered by provider."""
        self._ensure_loaded()
        results = []
        for tutorial in self._cache.values():
            if provider and tutorial.get("provider") != provider:
                continue
            results.append(self._summarise(tutorial))
        return results

    def get_tutorial(self, name: str) -> dict:
        """Return full tutorial dict (including steps) by name slug.

        Raises KeyError if the tutorial does not exist.
        """
        self._ensure_loaded()
        if name not in self._cache:
            raise KeyError(f"Tutorial not found: '{name}'")
        return self._cache[name]

    def start_tutorial(self, name: str) -> Any:
        """Create and store a new TutorialSession for the named tutorial.

        Returns the TutorialSession instance.
        Raises KeyError if the tutorial does not exist.
        """
        tutorial = self.get_tutorial(name)
        session = TutorialSession(
            tutorial_name=name,
            total_steps=len(tutorial.get("steps", [])),
        )
        self._sessions[session.session_id] = session
        logger.info("Started tutorial '%s' — session %s", name, session.session_id)
        return session

    def get_step(self, session_id: str, step_id: int) -> dict:
        """Return a step dict enriched with session context.

        Raises KeyError if session or step_id not found.
        """
        session = self._get_session(session_id)
        tutorial = self.get_tutorial(session.tutorial_name)
        step = self._find_step(tutorial, step_id)
        return {
            **step,
            "session_id": session_id,
            "is_completed": step_id in session.completed_steps,
            "is_current": session.current_step == step_id,
            "total_steps": session.total_steps,
        }

    def complete_step(self, session_id: str, step_id: int) -> dict:
        """Mark a step complete and advance the session cursor.

        Returns dict: session (summary), next_step (dict | None), tutorial_complete (bool).
        Raises KeyError if session or step_id not found.
        """
        session = self._get_session(session_id)
        tutorial = self.get_tutorial(session.tutorial_name)
        self._find_step(tutorial, step_id)  # validate step exists

        if step_id not in session.completed_steps:
            session.completed_steps.append(step_id)

        next_id = step_id + 1
        if next_id <= session.total_steps:
            session.current_step = next_id

        if session.is_complete and session.completed_at is None:
            session.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info("Tutorial '%s' completed — session %s", session.tutorial_name, session_id)

        next_step: dict | None = None
        if not session.is_complete:
            try:
                raw = self._find_step(tutorial, next_id)
                next_step = {
                    **raw,
                    "session_id": session_id,
                    "is_completed": False,
                    "is_current": True,
                    "total_steps": session.total_steps,
                }
            except KeyError:
                pass

        return {
            "session": session.to_dict(),
            "next_step": next_step,
            "tutorial_complete": session.is_complete,
        }

    def get_session(self, session_id: str) -> dict:
        """Return serialised session state dict. Raises KeyError if not found."""
        return self._get_session(session_id).to_dict()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Scan tutorial YAML files into cache — idempotent."""
        if self._loaded:
            return
        if not self._dir.exists():
            logger.warning("Tutorials directory not found: %s", self._dir)
            self._loaded = True
            return
        for yaml_file in sorted(self._dir.rglob("*.yaml")):
            try:
                data = self._parse_yaml(yaml_file)
                name = data.get("name")
                if not name:
                    logger.warning("Tutorial missing 'name' field: %s", yaml_file)
                    continue
                self._cache[name] = data
                logger.debug("Loaded tutorial '%s'", name)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", yaml_file, exc)
        self._loaded = True
        logger.info("Loaded %d tutorials from %s", len(self._cache), self._dir)

    @staticmethod
    def _parse_yaml(path: Path) -> dict:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML mapping, got {type(data).__name__}")
        return data

    @staticmethod
    def _summarise(tutorial: dict) -> dict:
        return {
            "name":          tutorial.get("name", ""),
            "title":         tutorial.get("title", ""),
            "provider":      tutorial.get("provider", ""),
            "difficulty":    tutorial.get("difficulty", ""),
            "duration":      tutorial.get("duration", ""),
            "prerequisites": tutorial.get("prerequisites", []),
            "concepts":      tutorial.get("concepts", []),
            "description":   tutorial.get("description", ""),
            "step_count":    len(tutorial.get("steps", [])),
        }

    def _get_session(self, session_id: str) -> Any:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session not found: '{session_id}'")
        return session

    @staticmethod
    def _find_step(tutorial: dict, step_id: int) -> dict:
        for step in tutorial.get("steps", []):
            if step.get("id") == step_id:
                return step
        raise KeyError(f"Step {step_id} not found in tutorial '{tutorial.get('name', '?')}'")
