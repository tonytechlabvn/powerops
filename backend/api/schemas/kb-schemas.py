"""Pydantic v2 schemas for Knowledge Base API endpoints."""
from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ChapterSummary(BaseModel):
    """Chapter list item with optional progress overlay."""
    slug: str
    title: str
    order: int
    difficulty: str
    estimated_minutes: int
    prerequisites: list[str] = []
    concepts: list[str] = []
    description: str = ""
    status: str = "not_started"
    quiz_score: int | None = None
    lab_completed: bool = False


class ContentSection(BaseModel):
    title: str
    body: str
    hcl_example: str | None = None


class ChapterDetail(BaseModel):
    """Full chapter content."""
    slug: str
    title: str
    order: int
    difficulty: str
    estimated_minutes: int
    prerequisites: list[str] = []
    concepts: list[str] = []
    powerops_features: list[str] = []
    content: dict


class QuizQuestion(BaseModel):
    """Quiz question — no correct answer exposed."""
    id: int
    type: str
    question: str
    options: list[str] | None = None


class QuizResponse(BaseModel):
    """Quiz questions for a chapter."""
    chapter_slug: str
    passing_score: int
    questions: list[QuizQuestion]


class QuizResultDetail(BaseModel):
    id: int
    correct: bool
    user_answer: int | bool
    correct_answer: int | bool
    explanation: str


class QuizResultResponse(BaseModel):
    """Result after quiz submission."""
    score: int
    passed: bool
    total: int
    correct_count: int
    details: list[QuizResultDetail]


class LabInfo(BaseModel):
    """Lab instructions for a chapter."""
    chapter_slug: str
    title: str
    description: str
    instructions: str
    starter_hcl: str
    hints: list[str] = []
    recommended_level: str
    available_levels: list[str] = ["pattern", "validate", "ai"]


class ValidationMessageSchema(BaseModel):
    level: str
    pattern: str | None = None
    passed: bool
    message: str


class LabValidationResponse(BaseModel):
    """Lab validation result."""
    level: str
    passed: bool
    messages: list[ValidationMessageSchema]


class UserProgress(BaseModel):
    """Overall user progress summary."""
    total_chapters: int
    completed: int
    in_progress: int
    not_started: int
    avg_quiz_score: float | None
    chapters: list[ChapterSummary]


class LeaderboardEntry(BaseModel):
    user_id: str
    display_name: str
    chapters_completed: int
    avg_quiz_score: float
    labs_completed: int
    total_score: float
    badges: list[str]


class LeaderboardResponse(BaseModel):
    scope: str
    entries: list[LeaderboardEntry]
    current_user_rank: int | None


class GlossaryConcept(BaseModel):
    term: str
    one_line: str
    explanation: str | None = None
    example: str | None = None
    related_concepts: list[str] | None = None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class QuizSubmission(BaseModel):
    """Quiz answers keyed by question id."""
    answers: dict[int, int | bool]


class LabValidationRequest(BaseModel):
    """Lab code submission for validation."""
    hcl_code: str
    level: str = "pattern"
