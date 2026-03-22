"""Leaderboard service — aggregation queries with TTL cache for KB rankings."""
from __future__ import annotations

import logging
import time

from sqlalchemy import select, func as sa_func, case, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import KBUserProgress, User, TeamMembership

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes
_cache: dict[str, tuple[float, list[dict]]] = {}

# Badge definitions — computed from completed chapter slugs
_BADGE_RULES = [
    ("first_step", ["iac-intro"]),
    ("terraform_practitioner", [
        "iac-intro", "hcl-syntax", "providers-init",
        "resources", "variables-outputs", "data-sources",
    ]),
    ("terraform_expert", [
        "iac-intro", "hcl-syntax", "providers-init", "resources",
        "variables-outputs", "data-sources", "state-management",
        "modules", "meta-arguments", "workspaces-environments",
        "cicd-vcs-workflows", "advanced-patterns",
    ]),
]


class Leaderboard:
    """Aggregates KB progress into ranked leaderboard entries."""

    @staticmethod
    async def get_leaderboard(
        session: AsyncSession,
        scope: str = "team",
        team_id: str | None = None,
    ) -> list[dict]:
        """Return ranked list of users with scores, badges."""
        cache_key = f"{scope}:{team_id or 'all'}"
        if Leaderboard._is_cache_valid(cache_key):
            return _cache[cache_key][1]

        # Build base query
        query = (
            select(
                User.id,
                User.name,
                sa_func.count(case(
                    (KBUserProgress.status == "completed", literal_column("1")),
                )).label("chapters_completed"),
                sa_func.coalesce(
                    sa_func.avg(case(
                        (KBUserProgress.quiz_score.isnot(None), KBUserProgress.quiz_score),
                    )), 0,
                ).label("avg_quiz_score"),
                sa_func.count(case(
                    (KBUserProgress.lab_completed == True, literal_column("1")),  # noqa: E712
                )).label("labs_completed"),
            )
            .outerjoin(KBUserProgress, User.id == KBUserProgress.user_id)
            .group_by(User.id, User.name)
        )

        # Scope filter
        if scope == "team" and team_id:
            query = query.where(
                User.id.in_(
                    select(TeamMembership.user_id).where(
                        TeamMembership.team_id == team_id
                    )
                )
            )

        result = await session.execute(query)
        rows = result.all()

        # Compute weighted scores and badges
        entries: list[dict] = []
        for row in rows:
            completed = row.chapters_completed or 0
            avg_score = float(row.avg_quiz_score or 0)
            labs = row.labs_completed or 0
            total_score = round(
                (completed / 12 * 50) + (avg_score / 100 * 30) + (labs / 12 * 20), 1,
            )
            # Get completed chapter slugs for badge computation
            badges = await Leaderboard._get_user_badges(session, row.id)
            entries.append({
                "user_id": row.id,
                "display_name": row.name or "Unknown",
                "chapters_completed": completed,
                "avg_quiz_score": round(avg_score, 1),
                "labs_completed": labs,
                "total_score": total_score,
                "badges": badges,
            })

        # Sort by total score descending
        entries.sort(key=lambda e: e["total_score"], reverse=True)

        # Cache result
        _cache[cache_key] = (time.time(), entries)
        return entries

    @staticmethod
    async def get_user_rank(
        session: AsyncSession,
        user_id: str,
        scope: str = "team",
        team_id: str | None = None,
    ) -> int | None:
        """Return 1-based rank for a user, or None if not on leaderboard."""
        entries = await Leaderboard.get_leaderboard(session, scope, team_id)
        for i, entry in enumerate(entries, 1):
            if entry["user_id"] == user_id:
                return i
        return None

    @staticmethod
    async def _get_user_badges(session: AsyncSession, user_id: str) -> list[str]:
        """Compute badges from user's completed chapter slugs."""
        result = await session.execute(
            select(KBUserProgress.chapter_slug).where(
                KBUserProgress.user_id == user_id,
                KBUserProgress.status == "completed",
            )
        )
        completed_slugs = set(result.scalars().all())
        return Leaderboard._compute_badges(completed_slugs)

    @staticmethod
    def _compute_badges(completed_slugs: set[str]) -> list[str]:
        """Deterministic badge computation from completed chapter slugs."""
        badges = []
        for badge_name, required_slugs in _BADGE_RULES:
            if all(s in completed_slugs for s in required_slugs):
                badges.append(badge_name)
        return badges

    @staticmethod
    def _is_cache_valid(key: str) -> bool:
        if key not in _cache:
            return False
        ts, _ = _cache[key]
        return (time.time() - ts) < CACHE_TTL
