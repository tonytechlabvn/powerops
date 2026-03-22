"""Curriculum loader — reads YAML chapter files and caches them in memory.

Follows the same pattern as TutorialEngine in backend/learning/tutorials.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CURRICULUM_DIR = Path(__file__).parent / "curriculum"


class CurriculumLoader:
    """Loads chapter YAML files from curriculum/ and caches by slug."""

    def __init__(self, curriculum_dir: Path | None = None) -> None:
        self._dir = curriculum_dir or _CURRICULUM_DIR
        self._cache: dict[str, dict] = {}
        self._ordered: list[dict] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_chapters(self) -> list[dict]:
        """Return summary list of all chapters sorted by order."""
        self._ensure_loaded()
        return [self._summarise(ch) for ch in self._ordered]

    def get_chapter(self, slug: str) -> dict | None:
        """Return full chapter dict by slug, or None if not found."""
        self._ensure_loaded()
        return self._cache.get(slug)

    def get_quiz(self, slug: str) -> dict | None:
        """Return quiz section with correct answers stripped for client display."""
        chapter = self.get_chapter(slug)
        if not chapter or "quiz" not in chapter:
            return None
        quiz = chapter["quiz"]
        stripped_questions = []
        for q in quiz.get("questions", []):
            safe_q = {
                "id": q["id"],
                "type": q["type"],
                "question": q["question"],
            }
            if q["type"] == "multiple_choice":
                safe_q["options"] = q.get("options", [])
            stripped_questions.append(safe_q)
        return {
            "chapter_slug": slug,
            "passing_score": quiz.get("passing_score", 70),
            "questions": stripped_questions,
        }

    def get_quiz_with_answers(self, slug: str) -> dict | None:
        """Return full quiz including correct answers (server-side only)."""
        chapter = self.get_chapter(slug)
        if not chapter or "quiz" not in chapter:
            return None
        return chapter["quiz"]

    def get_lab(self, slug: str) -> dict | None:
        """Return lab section of a chapter."""
        chapter = self.get_chapter(slug)
        if not chapter or "lab" not in chapter:
            return None
        return chapter["lab"]

    def get_chapter_order(self, slug: str) -> int | None:
        """Return chapter order number, or None if not found."""
        chapter = self.get_chapter(slug)
        return chapter.get("order") if chapter else None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Scan YAML files into cache — idempotent."""
        if self._loaded:
            return
        if not self._dir.exists():
            logger.warning("Curriculum directory not found: %s", self._dir)
            self._loaded = True
            return
        for yaml_file in sorted(self._dir.glob("*.yaml")):
            try:
                data = self._parse_yaml(yaml_file)
                slug = data.get("name")
                if not slug:
                    logger.warning("Chapter missing 'name' field: %s", yaml_file)
                    continue
                self._cache[slug] = data
                logger.debug("Loaded chapter '%s'", slug)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", yaml_file, exc)
        # Sort by order field and validate prerequisites
        self._ordered = sorted(self._cache.values(), key=lambda c: c.get("order", 999))
        self._validate_prerequisites()
        self._loaded = True
        logger.info("Loaded %d chapters from %s", len(self._cache), self._dir)

    def _validate_prerequisites(self) -> None:
        """Log warnings for prerequisite references that don't exist."""
        known_slugs = set(self._cache.keys())
        for ch in self._cache.values():
            for prereq in ch.get("prerequisites", []):
                if prereq not in known_slugs:
                    logger.warning(
                        "Chapter '%s' references unknown prerequisite '%s'",
                        ch.get("name"), prereq,
                    )

    @staticmethod
    def _parse_yaml(path: Path) -> dict:
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML mapping, got {type(data).__name__}")
        return data

    @staticmethod
    def _summarise(chapter: dict) -> dict:
        return {
            "slug": chapter.get("name", ""),
            "title": chapter.get("title", ""),
            "order": chapter.get("order", 0),
            "difficulty": chapter.get("difficulty", ""),
            "estimated_minutes": chapter.get("estimated_minutes", 0),
            "prerequisites": chapter.get("prerequisites", []),
            "concepts": chapter.get("concepts", []),
            "description": chapter.get("description", ""),
        }
