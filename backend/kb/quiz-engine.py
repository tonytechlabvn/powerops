"""Quiz engine — stateless scoring for KB curriculum quizzes."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuizResultDetail:
    """Per-question result after scoring."""
    id: int
    correct: bool
    user_answer: int | bool
    correct_answer: int | bool
    explanation: str


@dataclass
class QuizResult:
    """Aggregate quiz result."""
    score: int  # percentage 0-100
    passed: bool
    total: int
    correct_count: int
    details: list[QuizResultDetail] = field(default_factory=list)


class QuizEngine:
    """Stateless quiz scoring engine."""

    @staticmethod
    def score_quiz(
        chapter_slug: str,
        answers: dict[int, int | bool],
        loader,
    ) -> QuizResult:
        """Score user answers against the chapter quiz.

        Args:
            chapter_slug: Chapter identifier.
            answers: Map of question_id → user answer (MCQ: 0-based index, TF: bool).
            loader: CurriculumLoader instance.

        Returns:
            QuizResult with score, pass/fail, and per-question details.

        Raises:
            ValueError: If chapter or quiz not found.
        """
        quiz = loader.get_quiz_with_answers(chapter_slug)
        if not quiz:
            raise ValueError(f"Quiz not found for chapter '{chapter_slug}'")

        questions = quiz.get("questions", [])
        passing_score = quiz.get("passing_score", 70)
        total = len(questions)
        correct_count = 0
        details: list[QuizResultDetail] = []

        for q in questions:
            q_id = q["id"]
            user_ans = answers.get(q_id)
            correct_ans = q["correct"]
            explanation = q.get("explanation", "")

            is_correct = QuizEngine._check_answer(q["type"], user_ans, correct_ans)
            if is_correct:
                correct_count += 1

            details.append(QuizResultDetail(
                id=q_id,
                correct=is_correct,
                user_answer=user_ans if user_ans is not None else -1,
                correct_answer=correct_ans,
                explanation=explanation,
            ))

        score = round(correct_count / total * 100) if total > 0 else 0
        return QuizResult(
            score=score,
            passed=score >= passing_score,
            total=total,
            correct_count=correct_count,
            details=details,
        )

    @staticmethod
    def _check_answer(q_type: str, user_answer, correct_answer) -> bool:
        """Compare user answer to correct answer based on question type."""
        if user_answer is None:
            return False
        if q_type == "true_false":
            return bool(user_answer) == bool(correct_answer)
        # multiple_choice: compare int index
        return int(user_answer) == int(correct_answer)
