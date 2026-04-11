from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from postgrest import AsyncPostgrestClient

from ..schemas import AnswerIn, AnswerOut, QuestionOut, QuestionResultOut, ResultOut, SessionHistoryOut, SessionStartOut

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


async def create_session(db: AsyncPostgrestClient, student: dict, quiz_id: str) -> SessionStartOut:
    quiz_resp = await db.table("quizzes").select("id").eq("id", quiz_id).maybe_single().execute()
    if quiz_resp.data is None:
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

    first_question = questions[0]
    if int(first_question["question_number"]) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz questions must start at question_number 1.",
        )

    session_insert = await db.table("sessions").insert({"student_id": str(student["id"]), "quiz_id": quiz_id}).execute()
    session = session_insert.data[0] if session_insert is not None and session_insert.data else None
    if session is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create session.")

    return SessionStartOut(
        session_id=session["id"],
        question=_serialize_question(first_question),
        question_number=1,
        total=total,
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

    answers_resp = await db.table("answers").select("question_number").eq("session_id", str(session_id)).execute()
    answers = answers_resp.data or []
    expected_question_number = len(answers) + 1

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
    next_question = next_question_resp.data if next_question_resp is not None else None
    if next_question is None:
        await db.table("sessions").update({"ended_at": datetime.now(timezone.utc).isoformat()}).eq("id", str(session_id)).execute()
        return AnswerOut(done=True, session_id=session_id)

    total_resp = await db.table("questions").select("quiz_id", count="exact").eq("quiz_id", session["quiz_id"]).execute()
    total = total_resp.count if total_resp.count else 0
    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=int(next_question["question_number"]),
        total=int(total),
    )


async def get_result(db: AsyncPostgrestClient, session_id: UUID, student: dict) -> ResultOut:
    session = await _get_session_for_student(db, session_id, student["id"])
    if session.get("ended_at") is None:
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


async def list_session_history(db: AsyncPostgrestClient, student: dict) -> list[SessionHistoryOut]:
    sessions_resp = (
        await db.table("sessions")
        .select("id,quiz_id,started_at,ended_at")
        .eq("student_id", str(student["id"]))
        .order("started_at", desc=True)
        .execute()
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
            )
        )
    return history
