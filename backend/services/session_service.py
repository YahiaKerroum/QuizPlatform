from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Answer, Question, Quiz, Session, Student
from ..schemas import AnswerIn, AnswerOut, QuestionOut, QuestionResultOut, ResultOut, SessionHistoryOut, SessionStartOut

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}


def _serialize_question(question: Question) -> QuestionOut:
    return QuestionOut.model_validate(question)


def _normalize_choice(choice: str) -> str:
    normalized = choice.strip().lower()
    if normalized not in VALID_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chosen_answer must be one of a, b, c, d, e, or f.",
        )
    return normalized


def _choice_text(question: Question, choice: str) -> str | None:
    return getattr(question, f"choice_{choice}", None)


def _choice_image_url(question: Question, choice: str) -> str | None:
    return getattr(question, f"choice_{choice}_image_url", None)


async def _get_session_for_student(
    db: AsyncSession,
    session_id: UUID,
    student_id: UUID,
) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if session.student_id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    return session


async def create_session(db: AsyncSession, student: Student, quiz_id: str) -> SessionStartOut:
    quiz = await db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    total = await db.scalar(select(func.count()).select_from(Question).where(Question.quiz_id == quiz_id))
    if not total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz has no questions.",
        )

    first_question = await db.get(Question, (quiz_id, 1))
    if first_question is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz questions must start at question_number 1.",
        )

    session = Session(student_id=student.id, quiz_id=quiz_id)
    db.add(session)
    await db.flush()

    return SessionStartOut(
        session_id=session.id,
        question=_serialize_question(first_question),
        question_number=1,
        total=int(total),
    )


async def submit_answer(
    db: AsyncSession,
    session_id: UUID,
    student: Student,
    answer_in: AnswerIn,
) -> AnswerOut:
    session = await _get_session_for_student(db, session_id, student.id)
    if session.ended_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already complete.",
        )

    expected_question_number = int(
        await db.scalar(
            select(func.count()).select_from(Answer).where(Answer.session_id == session.id)
        )
        or 0
    ) + 1

    if answer_in.question_number != expected_question_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected question_number {expected_question_number}.",
        )

    if answer_in.response_time_ms <= 0 or answer_in.response_time_ms >= 600000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="response_time_ms must be between 1 and 599999.",
        )

    question = await db.get(Question, (session.quiz_id, answer_in.question_number))
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    chosen_answer = _normalize_choice(answer_in.chosen_answer)
    answer = Answer(
        session_id=session.id,
        quiz_id=session.quiz_id,
        question_number=question.question_number,
        chosen_answer=chosen_answer,
        is_correct=chosen_answer == question.correct_answer,
        response_time_ms=answer_in.response_time_ms,
    )
    db.add(answer)
    await db.flush()

    next_question = await db.get(Question, (session.quiz_id, expected_question_number + 1))
    if next_question is None:
        session.ended_at = datetime.now(timezone.utc)
        await db.flush()
        return AnswerOut(done=True, session_id=session.id)

    total = await db.scalar(select(func.count()).select_from(Question).where(Question.quiz_id == session.quiz_id))
    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=next_question.question_number,
        total=int(total or 0),
    )


async def get_result(db: AsyncSession, session_id: UUID, student: Student) -> ResultOut:
    session = await _get_session_for_student(db, session_id, student.id)
    if session.ended_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not complete yet.",
        )

    result = await db.execute(
        select(Answer, Question)
        .join(
            Question,
            and_(
                Question.quiz_id == Answer.quiz_id,
                Question.question_number == Answer.question_number,
            ),
        )
        .where(Answer.session_id == session.id)
        .order_by(Answer.question_number.asc())
    )
    rows = result.all()

    total = len(rows)
    correct = sum(1 for answer, _question in rows if answer.is_correct)
    accuracy = (correct / total) if total else 0.0

    by_difficulty_raw: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    by_question: list[QuestionResultOut] = []

    for answer, question in rows:
        difficulty_key = question.difficulty or "unassigned"
        by_difficulty_raw[difficulty_key]["total"] += 1
        if answer.is_correct:
            by_difficulty_raw[difficulty_key]["correct"] += 1

        by_question.append(
            QuestionResultOut(
                question_number=answer.question_number,
                question_text=question.question_text,
                question_image_url=question.question_image_url,
                chosen_answer=answer.chosen_answer,
                correct_answer=question.correct_answer,
                chosen_answer_text=_choice_text(question, answer.chosen_answer),
                chosen_answer_image_url=_choice_image_url(question, answer.chosen_answer),
                correct_answer_text=_choice_text(question, question.correct_answer) or question.correct_answer.upper(),
                correct_answer_image_url=_choice_image_url(question, question.correct_answer),
                is_correct=answer.is_correct,
                response_time_ms=answer.response_time_ms,
                difficulty=question.difficulty,
                answered_at=answer.answered_at,
            )
        )

    by_difficulty = {
        key: {
            "total": value["total"],
            "correct": value["correct"],
            "accuracy": (value["correct"] / value["total"]) if value["total"] else 0.0,
        }
        for key, value in by_difficulty_raw.items()
    }

    return ResultOut(
        total=total,
        correct=correct,
        accuracy=accuracy,
        by_difficulty=by_difficulty,
        by_question=by_question,
    )


async def list_session_history(db: AsyncSession, student: Student) -> list[SessionHistoryOut]:
    result = await db.execute(
        select(
            Session.id.label("session_id"),
            Session.quiz_id,
            Quiz.display_name,
            Session.started_at,
            Session.ended_at,
            func.count(Answer.id).label("total"),
            func.coalesce(func.sum(Answer.is_correct.cast(Integer)), 0).label("correct"),
        )
        .join(Quiz, Quiz.id == Session.quiz_id)
        .outerjoin(Answer, Answer.session_id == Session.id)
        .where(Session.student_id == student.id)
        .group_by(Session.id, Session.quiz_id, Quiz.display_name, Session.started_at, Session.ended_at)
        .order_by(Session.started_at.desc())
    )

    history: list[SessionHistoryOut] = []
    for row in result.all():
        total = int(row.total or 0)
        correct = int(row.correct or 0)
        history.append(
            SessionHistoryOut(
                session_id=row.session_id,
                quiz_id=row.quiz_id,
                display_name=row.display_name,
                started_at=row.started_at,
                ended_at=row.ended_at,
                total=total,
                correct=correct,
                accuracy=(correct / total) if total else 0.0,
            )
        )
    return history
