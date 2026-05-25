from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Integer, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Answer, Question, Quiz, Session, Student
from ..schemas import AnswerIn, AnswerOut, QuestionOut, QuestionResultOut, ResultOut, SessionHistoryOut, SessionStartOut
from . import ml_service

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


async def create_session(db: AsyncSession, student: Student, quiz_id: str, adaptive: bool = False) -> SessionStartOut:
    quiz = await db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    total = await db.scalar(select(func.count()).select_from(Question).where(Question.quiz_id == quiz_id))
    if not total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz has no questions.",
        )

    if adaptive:
        # Cold-start: pick the easiest available question first
        result = await db.execute(
            select(Question)
            .where(Question.quiz_id == quiz_id, Question.difficulty == "easy")
            .order_by(Question.question_number)
            .limit(1)
        )
        first_question = result.scalar_one_or_none()
        if first_question is None:
            first_question = await db.get(Question, (quiz_id, 1))
    else:
        first_question = await db.get(Question, (quiz_id, 1))

    if first_question is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz questions must start at question_number 1.",
        )

    session = Session(student_id=student.id, quiz_id=quiz_id, is_adaptive=adaptive)
    db.add(session)
    await db.flush()

    return SessionStartOut(
        session_id=session.id,
        question=_serialize_question(first_question),
        question_number=first_question.question_number,
        total=int(total),
        is_adaptive=adaptive,
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

    if session.is_adaptive:
        # Adaptive: any unanswered question is valid — no sequential order enforced
        already = await db.scalar(
            select(func.count()).select_from(Answer).where(
                and_(Answer.session_id == session.id, Answer.question_number == answer_in.question_number)
            )
        )
        if already:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question already answered.")
    else:
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

    total = await db.scalar(select(func.count()).select_from(Question).where(Question.quiz_id == session.quiz_id))

    if session.is_adaptive:
        return await _submit_adaptive(db, session, int(total or 0))

    next_question = await db.get(Question, (session.quiz_id, expected_question_number + 1))
    if next_question is None:
        session.ended_at = datetime.now(timezone.utc)
        await db.flush()
        return AnswerOut(done=True, session_id=session.id)

    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=next_question.question_number,
        total=int(total or 0),
    )


async def _submit_adaptive(db: AsyncSession, session: Session, total: int) -> AnswerOut:
    """Select the next question using the ML model and check the stop criterion."""
    # Load full answer history for this session
    history_result = await db.execute(
        select(Answer, Question)
        .join(Question, and_(Question.quiz_id == Answer.quiz_id, Question.question_number == Answer.question_number))
        .where(Answer.session_id == session.id)
        .order_by(Answer.answered_at.asc())
    )
    history_rows = history_result.all()
    n_answered = len(history_rows)

    is_correct_list = [bool(a.is_correct) for a, _ in history_rows]
    difficulty_list = [q.difficulty for _, q in history_rows]
    time_ms_list    = [int(a.response_time_ms) for a, _ in history_rows]

    # Use the quiz's module_id so per-module features match training slugs
    quiz_obj = await db.get(Quiz, session.quiz_id)
    quiz_module = quiz_obj.module_id if quiz_obj and quiz_obj.module_id else None
    module_list = [quiz_module] * n_answered

    features = ml_service.compute_features(is_correct_list, difficulty_list, time_ms_list, module_list)
    prediction = ml_service.predict_level(features)
    predicted_level = prediction["level"]
    confidence      = prediction["confidence"]

    # Check stop criterion
    if ml_service.should_stop(features, n_answered):
        session.ended_at = datetime.now(timezone.utc)
        await db.flush()
        return AnswerOut(
            done=True,
            session_id=session.id,
            predicted_level=predicted_level,
            confidence=confidence,
        )

    # Load all unanswered questions
    answered_nums_result = await db.execute(
        select(Answer.question_number).where(Answer.session_id == session.id)
    )
    answered_nums = {row[0] for row in answered_nums_result.all()}

    remaining_result = await db.execute(
        select(Question)
        .where(Question.quiz_id == session.quiz_id)
        .order_by(Question.question_number)
    )
    remaining = [q for q in remaining_result.scalars().all() if q.question_number not in answered_nums]

    if not remaining:
        session.ended_at = datetime.now(timezone.utc)
        await db.flush()
        return AnswerOut(done=True, session_id=session.id, predicted_level=predicted_level, confidence=confidence)

    candidate_nums  = [q.question_number for q in remaining]
    candidate_diffs = [q.difficulty for q in remaining]
    next_num = ml_service.select_next_question(features, candidate_nums, candidate_diffs, strategy="entropy")
    next_question = next((q for q in remaining if q.question_number == next_num), remaining[0])

    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=next_question.question_number,
        total=total,
        predicted_level=predicted_level,
        confidence=confidence,
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
            Session.is_adaptive,
            Quiz.display_name,
            Session.started_at,
            Session.ended_at,
            func.count(Answer.id).label("total"),
            func.coalesce(func.sum(Answer.is_correct.cast(Integer)), 0).label("correct"),
        )
        .join(Quiz, Quiz.id == Session.quiz_id)
        .outerjoin(Answer, Answer.session_id == Session.id)
        .where(Session.student_id == student.id)
        .group_by(Session.id, Session.quiz_id, Session.is_adaptive, Quiz.display_name, Session.started_at, Session.ended_at)
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
                is_adaptive=bool(row.is_adaptive),
            )
        )
    return history
