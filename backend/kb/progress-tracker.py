"""Progress tracker — DB CRUD for per-user KB chapter progress."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import KBUserProgress

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Async DB operations for user progress in KB curriculum."""

    @staticmethod
    async def get_user_progress(session: AsyncSession, user_id: str) -> list[KBUserProgress]:
        """Return all progress records for a user."""
        result = await session.execute(
            select(KBUserProgress).where(KBUserProgress.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_chapter_progress(
        session: AsyncSession, user_id: str, slug: str,
    ) -> KBUserProgress | None:
        """Return progress for a specific chapter, or None."""
        result = await session.execute(
            select(KBUserProgress).where(
                KBUserProgress.user_id == user_id,
                KBUserProgress.chapter_slug == slug,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def start_chapter(
        session: AsyncSession, user_id: str, slug: str,
    ) -> KBUserProgress:
        """Mark a chapter as started. Creates record if not exists."""
        record = await ProgressTracker.get_chapter_progress(session, user_id, slug)
        now = datetime.now(timezone.utc)
        if record is None:
            record = KBUserProgress(
                user_id=user_id,
                chapter_slug=slug,
                status="in_progress",
                started_at=now,
            )
            session.add(record)
        elif record.status == "not_started":
            record.status = "in_progress"
            record.started_at = now
        await session.flush()
        return record

    @staticmethod
    async def update_quiz(
        session: AsyncSession, user_id: str, slug: str,
        score: int, passed: bool,
    ) -> KBUserProgress:
        """Update quiz score and increment attempts."""
        record = await ProgressTracker.get_chapter_progress(session, user_id, slug)
        if record is None:
            # Auto-start if not started
            record = await ProgressTracker.start_chapter(session, user_id, slug)
        record.quiz_score = score
        record.quiz_attempts += 1
        await session.flush()
        return record

    @staticmethod
    async def update_lab(
        session: AsyncSession, user_id: str, slug: str,
        code: str, level: str, completed: bool,
    ) -> KBUserProgress:
        """Update lab submission fields."""
        record = await ProgressTracker.get_chapter_progress(session, user_id, slug)
        if record is None:
            record = await ProgressTracker.start_chapter(session, user_id, slug)
        record.lab_code = code
        record.lab_validation_level = level
        if completed:
            record.lab_completed = True
        await session.flush()
        return record

    @staticmethod
    async def complete_chapter(
        session: AsyncSession, user_id: str, slug: str,
    ) -> KBUserProgress:
        """Mark a chapter as completed."""
        record = await ProgressTracker.get_chapter_progress(session, user_id, slug)
        if record is None:
            record = await ProgressTracker.start_chapter(session, user_id, slug)
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        await session.flush()
        return record

    @staticmethod
    async def get_curriculum_with_progress(
        session: AsyncSession, user_id: str, loader,
    ) -> dict:
        """Merge chapter list with user progress for overview display."""
        chapters = loader.list_chapters()
        progress_records = await ProgressTracker.get_user_progress(session, user_id)
        progress_map = {r.chapter_slug: r for r in progress_records}

        enriched = []
        completed = 0
        in_progress = 0
        not_started = 0
        quiz_scores: list[int] = []

        for ch in chapters:
            record = progress_map.get(ch["slug"])
            ch_data = {
                **ch,
                "status": record.status if record else "not_started",
                "quiz_score": record.quiz_score if record else None,
                "lab_completed": record.lab_completed if record else False,
            }
            enriched.append(ch_data)

            if record and record.status == "completed":
                completed += 1
            elif record and record.status == "in_progress":
                in_progress += 1
            else:
                not_started += 1

            if record and record.quiz_score is not None:
                quiz_scores.append(record.quiz_score)

        avg_score = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else None

        return {
            "total_chapters": len(chapters),
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
            "avg_quiz_score": avg_score,
            "chapters": enriched,
        }
