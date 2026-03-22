"""Knowledge Base API routes — curriculum, quizzes, labs, progress, glossary.

Endpoints:
  GET    /api/kb/curriculum              — chapters + user progress
  GET    /api/kb/chapters/{slug}         — full chapter content
  POST   /api/kb/chapters/{slug}/start   — mark chapter started
  GET    /api/kb/chapters/{slug}/quiz    — quiz questions (no answers)
  POST   /api/kb/chapters/{slug}/quiz    — submit quiz answers
  GET    /api/kb/chapters/{slug}/lab     — lab instructions + starter
  POST   /api/kb/chapters/{slug}/lab/validate — validate HCL code
  POST   /api/kb/chapters/{slug}/complete — mark chapter completed
  GET    /api/kb/progress                — user overall progress
  GET    /api/kb/leaderboard             — team/org rankings
  GET    /api/kb/glossary                — all glossary concepts
  GET    /api/kb/glossary/{term}         — single glossary concept
"""
from __future__ import annotations

import importlib.util as _ilu
import logging
import sys as _sys
from pathlib import Path as _P

from fastapi import APIRouter, HTTPException, Request

from backend.db.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


# ---------------------------------------------------------------------------
# Lazy loaders for kebab-case modules
# ---------------------------------------------------------------------------

def _load(rel: str, alias: str):
    full = f"backend.{alias}"
    if full in _sys.modules:
        return _sys.modules[full]
    base = _P(__file__).resolve().parent.parent
    spec = _ilu.spec_from_file_location(full, base / rel)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _schemas():
    return _load("schemas/kb-schemas.py", "api.schemas.kb_schemas")


def _kb():
    """Return the KB package (curriculum loader, quiz engine, etc.)."""
    full = "backend.kb"
    if full in _sys.modules:
        return _sys.modules[full]
    # __init__.py handles imports
    import backend.kb as kb
    return kb


def _glossary():
    return _load("../learning/glossary.py", "learning.glossary")


# Singleton instances (created on first use)
_loader_instance = None
_quiz_engine_instance = None
_lab_validator_instance = None


def _get_loader():
    global _loader_instance
    if _loader_instance is None:
        kb = _kb()
        _loader_instance = kb.CurriculumLoader()
    return _loader_instance


def _get_quiz_engine():
    global _quiz_engine_instance
    if _quiz_engine_instance is None:
        kb = _kb()
        _quiz_engine_instance = kb.QuizEngine()
    return _quiz_engine_instance


def _get_lab_validator():
    global _lab_validator_instance
    if _lab_validator_instance is None:
        kb = _kb()
        _lab_validator_instance = kb.LabValidator()
    return _lab_validator_instance


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_auth(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not isinstance(user, dict):
        raise HTTPException(401, "Not authenticated")
    return user


# ---------------------------------------------------------------------------
# Curriculum endpoints
# ---------------------------------------------------------------------------

@router.get("/curriculum")
async def list_curriculum(request: Request):
    """List all chapters with user's progress overlay."""
    user = _require_auth(request)
    loader = _get_loader()
    kb = _kb()
    async with get_session() as session:
        data = await kb.ProgressTracker.get_curriculum_with_progress(
            session, user["user_id"], loader,
        )
    S = _schemas()
    return S.UserProgress(**data)


@router.get("/chapters/{slug}")
async def get_chapter(slug: str, request: Request):
    """Return full chapter content."""
    _require_auth(request)
    loader = _get_loader()
    chapter = loader.get_chapter(slug)
    if not chapter:
        raise HTTPException(404, f"Chapter '{slug}' not found")
    S = _schemas()
    return S.ChapterDetail(
        slug=chapter.get("name", slug),
        title=chapter.get("title", ""),
        order=chapter.get("order", 0),
        difficulty=chapter.get("difficulty", ""),
        estimated_minutes=chapter.get("estimated_minutes", 0),
        prerequisites=chapter.get("prerequisites", []),
        concepts=chapter.get("concepts", []),
        powerops_features=chapter.get("powerops_features", []),
        content=chapter.get("content", {}),
    )


@router.post("/chapters/{slug}/start")
async def start_chapter(slug: str, request: Request):
    """Mark a chapter as started for the current user."""
    user = _require_auth(request)
    loader = _get_loader()
    if not loader.get_chapter(slug):
        raise HTTPException(404, f"Chapter '{slug}' not found")
    kb = _kb()
    async with get_session() as session:
        await kb.ProgressTracker.start_chapter(session, user["user_id"], slug)
        await session.commit()
    return {"status": "ok", "chapter": slug}


# ---------------------------------------------------------------------------
# Quiz endpoints
# ---------------------------------------------------------------------------

@router.get("/chapters/{slug}/quiz")
async def get_quiz(slug: str, request: Request):
    """Return quiz questions without correct answers."""
    _require_auth(request)
    loader = _get_loader()
    quiz = loader.get_quiz(slug)
    if not quiz:
        raise HTTPException(404, f"Quiz not found for chapter '{slug}'")
    S = _schemas()
    return S.QuizResponse(**quiz)


@router.post("/chapters/{slug}/quiz")
async def submit_quiz(slug: str, request: Request):
    """Submit quiz answers and get scored result."""
    user = _require_auth(request)
    S = _schemas()
    body = S.QuizSubmission(**(await request.json()))

    loader = _get_loader()
    quiz_engine = _get_quiz_engine()

    try:
        result = quiz_engine.score_quiz(slug, body.answers, loader)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

    # Persist quiz result
    kb = _kb()
    async with get_session() as session:
        await kb.ProgressTracker.update_quiz(
            session, user["user_id"], slug, result.score, result.passed,
        )
        await session.commit()

    return S.QuizResultResponse(
        score=result.score,
        passed=result.passed,
        total=result.total,
        correct_count=result.correct_count,
        details=[
            S.QuizResultDetail(
                id=d.id,
                correct=d.correct,
                user_answer=d.user_answer,
                correct_answer=d.correct_answer,
                explanation=d.explanation,
            )
            for d in result.details
        ],
    )


# ---------------------------------------------------------------------------
# Lab endpoints
# ---------------------------------------------------------------------------

@router.get("/chapters/{slug}/lab")
async def get_lab(slug: str, request: Request):
    """Return lab instructions, starter code, and recommended validation level."""
    _require_auth(request)
    loader = _get_loader()
    lab = loader.get_lab(slug)
    if not lab:
        raise HTTPException(404, f"Lab not found for chapter '{slug}'")

    validator = _get_lab_validator()
    chapter_order = loader.get_chapter_order(slug) or 1
    recommended = validator.recommend_level(chapter_order)

    S = _schemas()
    return S.LabInfo(
        chapter_slug=slug,
        title=lab.get("title", ""),
        description=lab.get("description", ""),
        instructions=lab.get("instructions", ""),
        starter_hcl=lab.get("starter_hcl", ""),
        hints=lab.get("hints", []),
        recommended_level=recommended,
    )


@router.post("/chapters/{slug}/lab/validate")
async def validate_lab(slug: str, request: Request):
    """Validate user-submitted HCL code at the requested level."""
    user = _require_auth(request)
    S = _schemas()
    body = S.LabValidationRequest(**(await request.json()))

    loader = _get_loader()
    validator = _get_lab_validator()

    result = validator.validate(body.hcl_code, slug, body.level, loader)

    # Persist lab submission if validation passed
    if result.passed:
        kb = _kb()
        async with get_session() as session:
            await kb.ProgressTracker.update_lab(
                session, user["user_id"], slug, body.hcl_code, body.level, True,
            )
            await session.commit()

    return S.LabValidationResponse(
        level=result.level,
        passed=result.passed,
        messages=[
            S.ValidationMessageSchema(
                level=m.level, pattern=m.pattern, passed=m.passed, message=m.message,
            )
            for m in result.messages
        ],
    )


# ---------------------------------------------------------------------------
# Progress / completion endpoints
# ---------------------------------------------------------------------------

@router.post("/chapters/{slug}/complete")
async def complete_chapter(slug: str, request: Request):
    """Mark chapter as completed. Requires quiz passed + lab completed."""
    user = _require_auth(request)
    kb = _kb()
    async with get_session() as session:
        progress = await kb.ProgressTracker.get_chapter_progress(
            session, user["user_id"], slug,
        )
        if not progress:
            raise HTTPException(400, "Chapter not started")
        if not progress.quiz_score or progress.quiz_score < 70:
            raise HTTPException(400, "Quiz not passed (need >= 70%)")
        if not progress.lab_completed:
            raise HTTPException(400, "Lab not completed")
        await kb.ProgressTracker.complete_chapter(session, user["user_id"], slug)
        await session.commit()
    return {"status": "ok", "chapter": slug, "completed": True}


@router.get("/progress")
async def get_progress(request: Request):
    """Return user's overall curriculum progress."""
    user = _require_auth(request)
    loader = _get_loader()
    kb = _kb()
    async with get_session() as session:
        data = await kb.ProgressTracker.get_curriculum_with_progress(
            session, user["user_id"], loader,
        )
    S = _schemas()
    return S.UserProgress(**data)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def _leaderboard_service():
    """Lazy load leaderboard module."""
    full = "backend.kb.leaderboard"
    if full in _sys.modules:
        return _sys.modules[full]
    base = _P(__file__).resolve().parent.parent.parent  # backend/
    spec = _ilu.spec_from_file_location(full, base / "kb" / "leaderboard.py")
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@router.get("/leaderboard")
async def get_leaderboard(request: Request, scope: str = "team"):
    """Return leaderboard rankings for team or org scope."""
    user = _require_auth(request)
    lb = _leaderboard_service().Leaderboard

    # Determine team_id from user's team membership
    team_id = user.get("team_id")

    S = _schemas()
    async with get_session() as session:
        entries = await lb.get_leaderboard(session, scope, team_id)
        rank = await lb.get_user_rank(session, user["user_id"], scope, team_id)

    return S.LeaderboardResponse(
        scope=scope,
        entries=[S.LeaderboardEntry(**e) for e in entries],
        current_user_rank=rank,
    )


# ---------------------------------------------------------------------------
# Glossary proxy endpoints
# ---------------------------------------------------------------------------

@router.get("/glossary")
async def list_glossary(request: Request):
    """Return all glossary concepts."""
    _require_auth(request)
    glossary = _glossary()
    concepts = glossary.list_concepts()
    S = _schemas()
    return [S.GlossaryConcept(**c) for c in concepts]


@router.get("/glossary/{term}")
async def get_glossary_term(term: str, request: Request):
    """Return a single glossary concept by term."""
    _require_auth(request)
    glossary = _glossary()
    concept = glossary.get_concept(term)
    if not concept:
        raise HTTPException(404, f"Glossary term '{term}' not found")
    S = _schemas()
    return S.GlossaryConcept(**concept)
