from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from postgrest import AsyncPostgrestClient

from ..schemas import AnswerIn, AnswerOut, QuestionOut, QuestionResultOut, ResultOut, SessionHistoryOut, SessionStartOut
from . import ml_service

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}


def _serialize_question(question: dict) -> QuestionOut:
    return QuestionOut.model_validate(question)


def _normalize_choice(choice: str) -> str:
    normalized = choice.strip().lower()
    if normalized not in VALID_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chosen_answer must be one of a, b, c, d, e, or f.",
        )
    return normalized


def _choice_text(question: dict, choice: str) -> str | None:
    return question.get(f"choice_{choice}")


def _choice_image_url(question: dict, choice: str) -> str | None:
    return question.get(f"choice_{choice}_image_url")


async def _get_session_for_student(
    db: AsyncPostgrestClient,
    session_id: UUID,
    student_id: UUID,
) -> dict:
    response = await db.table("sessions").select("*").eq("id", str(session_id)).maybe_single().execute()
    session = response.data
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if str(session["student_id"]) != str(student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    return session


async def create_session(db: AsyncSession, student: Student, quiz_id: str, adaptive: bool = False) -> SessionStartOut:
    quiz = await db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    questions_resp = (
        await db.table("questions")
        .select("*")
        .eq("quiz_id", quiz_id)
        .order("question_number")
        .execute()
    )
    questions = questions_resp.data or []
    total = len(questions)
    if total == 0:
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
        session_id=session["id"],
        question=_serialize_question(first_question),
        question_number=first_question.question_number,
        total=int(total),
        is_adaptive=adaptive,
    )


async def submit_answer(
    db: AsyncPostgrestClient,
    session_id: UUID,
    student: dict,
    answer_in: AnswerIn,
) -> AnswerOut:
    session = await _get_session_for_student(db, session_id, student["id"])
    if session.get("ended_at") is not None:
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

    question_resp = (
        await db.table("questions")
        .select("*")
        .eq("quiz_id", session["quiz_id"])
        .eq("question_number", answer_in.question_number)
        .maybe_single()
        .execute()
    )
    question = question_resp.data
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found.",
        )

    chosen_answer = _normalize_choice(answer_in.chosen_answer)
    await db.table("answers").insert(
        {
            "session_id": str(session_id),
            "quiz_id": session["quiz_id"],
            "question_number": int(question["question_number"]),
            "chosen_answer": chosen_answer,
            "is_correct": chosen_answer == question["correct_answer"],
            "response_time_ms": answer_in.response_time_ms,
        }
    ).execute()

    next_question_resp = (
        await db.table("questions")
        .select("*")
        .eq("quiz_id", session["quiz_id"])
        .eq("question_number", expected_question_number + 1)
        .maybe_single()
        .execute()
    )
    db.add(answer)
    await db.flush()

    total = await db.scalar(select(func.count()).select_from(Question).where(Question.quiz_id == session.quiz_id))

    if session.is_adaptive:
        return await _submit_adaptive(db, session, int(total or 0))

    next_question = await db.get(Question, (session.quiz_id, expected_question_number + 1))
    if next_question is None:
        await db.table("sessions").update({"ended_at": datetime.now(timezone.utc).isoformat()}).eq("id", str(session_id)).execute()
        return AnswerOut(done=True, session_id=session_id)

    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=int(next_question["question_number"]),
        total=int(total),
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

    answers_resp = (
        await db.table("answers")
        .select("*")
        .eq("session_id", str(session_id))
        .order("question_number")
        .execute()
    )
    answers = answers_resp.data or []

    question_numbers = [int(answer["question_number"]) for answer in answers]
    questions_resp = await db.table("questions").select("*").eq("quiz_id", session["quiz_id"]).execute()
    all_questions = questions_resp.data or []
    questions_by_number = {int(q["question_number"]): q for q in all_questions}

    total = len(answers)
    correct = sum(1 for answer in answers if answer.get("is_correct"))
    accuracy = (correct / total) if total else 0.0

    by_difficulty_raw: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    by_question: list[QuestionResultOut] = []

    for answer in answers:
        question = questions_by_number.get(int(answer["question_number"]))
        if question is None:
            continue

        difficulty_key = question.get("difficulty") or "unassigned"
        by_difficulty_raw[difficulty_key]["total"] += 1
        if answer.get("is_correct"):
            by_difficulty_raw[difficulty_key]["correct"] += 1

        chosen_answer = answer["chosen_answer"]
        correct_answer = question["correct_answer"]
        by_question.append(
            QuestionResultOut(
                question_number=int(answer["question_number"]),
                question_text=question["question_text"],
                question_image_url=question.get("question_image_url"),
                chosen_answer=chosen_answer,
                correct_answer=correct_answer,
                chosen_answer_text=_choice_text(question, chosen_answer),
                chosen_answer_image_url=_choice_image_url(question, chosen_answer),
                correct_answer_text=_choice_text(question, correct_answer) or correct_answer.upper(),
                correct_answer_image_url=_choice_image_url(question, correct_answer),
                is_correct=bool(answer.get("is_correct")),
                response_time_ms=int(answer["response_time_ms"]),
                difficulty=question.get("difficulty"),
                answered_at=answer["answered_at"],
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
    sessions = sessions_resp.data or []
    if not sessions:
        return []

    quiz_ids = sorted({row["quiz_id"] for row in sessions})
    quizzes_resp = await db.table("quizzes").select("id,display_name").in_("id", quiz_ids).execute()
    quiz_name_by_id = {row["id"]: row["display_name"] for row in (quizzes_resp.data or [])}

    session_ids = [row["id"] for row in sessions]
    answers_resp = await db.table("answers").select("session_id,is_correct").in_("session_id", session_ids).execute()
    answers = answers_resp.data or []

    totals: dict[str, int] = defaultdict(int)
    corrects: dict[str, int] = defaultdict(int)
    for answer in answers:
        sid = answer["session_id"]
        totals[sid] += 1
        if answer.get("is_correct"):
            corrects[sid] += 1

    history: list[SessionHistoryOut] = []
    for row in sessions:
        sid = row["id"]
        total = int(totals.get(sid, 0))
        correct = int(corrects.get(sid, 0))
        history.append(
            SessionHistoryOut(
                session_id=sid,
                quiz_id=row["quiz_id"],
                display_name=quiz_name_by_id.get(row["quiz_id"], row["quiz_id"]),
                started_at=row["started_at"],
                ended_at=row.get("ended_at"),
                total=total,
                correct=correct,
                accuracy=(correct / total) if total else 0.0,
                is_adaptive=bool(row.is_adaptive),
            )
        )
    return history
