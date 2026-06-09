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
    student_id: str,
) -> dict:
    response = await db.table("sessions").select("*").eq("id", str(session_id)).maybe_single().execute()
    session = response.data if response is not None else None
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if str(session["student_id"]) != str(student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    return session


async def create_session(
    db: AsyncPostgrestClient,
    student: dict,
    quiz_id: str,
    adaptive: bool = False,
) -> SessionStartOut:
    quiz_resp = await db.table("quizzes").select("id").eq("id", quiz_id).maybe_single().execute()
    if quiz_resp is None or quiz_resp.data is None:
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
        easy = [q for q in questions if q.get("difficulty") == "easy"]
        first_question = easy[0] if easy else questions[0]
    else:
        first_by_number = [q for q in questions if int(q["question_number"]) == 1]
        if not first_by_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz questions must start at question_number 1.",
            )
        first_question = first_by_number[0]

    session_insert = await db.table("sessions").insert({
        "student_id": str(student["id"]),
        "quiz_id": quiz_id,
        "is_adaptive": adaptive,
    }).execute()

    session = session_insert.data[0] if session_insert and session_insert.data else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session.",
        )

    return SessionStartOut(
        session_id=session["id"],
        question=_serialize_question(first_question),
        question_number=int(first_question["question_number"]),
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

    answers_resp = (
        await db.table("answers")
        .select("question_number")
        .eq("session_id", str(session_id))
        .execute()
    )
    existing_answers = answers_resp.data or []
    answered_nums = {int(a["question_number"]) for a in existing_answers}

    if session.get("is_adaptive"):
        if answer_in.question_number in answered_nums:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question already answered.")
    else:
        expected = len(existing_answers) + 1
        if answer_in.question_number != expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected question_number {expected}.",
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    chosen_answer = _normalize_choice(answer_in.chosen_answer)
    await db.table("answers").insert({
        "session_id": str(session_id),
        "quiz_id": session["quiz_id"],
        "question_number": int(question["question_number"]),
        "chosen_answer": chosen_answer,
        "is_correct": chosen_answer == question["correct_answer"],
        "response_time_ms": answer_in.response_time_ms,
    }).execute()

    answered_nums.add(answer_in.question_number)

    total_resp = (
        await db.table("questions")
        .select("question_number")
        .eq("quiz_id", session["quiz_id"])
        .execute()
    )
    total = len(total_resp.data or [])

    if session.get("is_adaptive"):
        return await _submit_adaptive(db, session, session_id, total)

    next_num = len(answered_nums) + 1
    next_q_resp = (
        await db.table("questions")
        .select("*")
        .eq("quiz_id", session["quiz_id"])
        .eq("question_number", next_num)
        .maybe_single()
        .execute()
    )
    next_question = next_q_resp.data if next_q_resp is not None else None

    if next_question is None:
        await db.table("sessions").update(
            {"ended_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(session_id)).execute()
        return AnswerOut(done=True, session_id=session_id)

    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=int(next_question["question_number"]),
        total=int(total),
    )


async def _submit_adaptive(
    db: AsyncPostgrestClient,
    session: dict,
    session_id: UUID,
    total: int,
) -> AnswerOut:
    answers_resp = (
        await db.table("answers")
        .select("*")
        .eq("session_id", str(session_id))
        .order("answered_at")
        .execute()
    )
    answers = answers_resp.data or []
    n_answered = len(answers)

    all_q_resp = (
        await db.table("questions")
        .select("*")
        .eq("quiz_id", session["quiz_id"])
        .execute()
    )
    all_questions = all_q_resp.data or []
    q_by_num = {int(q["question_number"]): q for q in all_questions}

    is_correct_list = [bool(a["is_correct"]) for a in answers]
    difficulty_list = [q_by_num.get(int(a["question_number"]), {}).get("difficulty") for a in answers]
    time_ms_list = [int(a["response_time_ms"]) for a in answers]

    quiz_resp = (
        await db.table("quizzes")
        .select("module_id")
        .eq("id", session["quiz_id"])
        .maybe_single()
        .execute()
    )
    quiz_module = quiz_resp.data.get("module_id") if quiz_resp and quiz_resp.data else None
    module_list = [quiz_module] * n_answered

    features = ml_service.compute_features(is_correct_list, difficulty_list, time_ms_list, module_list)
    prediction = ml_service.predict_level(features)
    predicted_level = prediction["level"]
    confidence = prediction["confidence"]

    if ml_service.should_stop(features, n_answered):
        await db.table("sessions").update(
            {"ended_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(session_id)).execute()
        return AnswerOut(
            done=True,
            session_id=session_id,
            predicted_level=predicted_level,
            confidence=confidence,
        )

    answered_nums = {int(a["question_number"]) for a in answers}
    remaining = [q for q in all_questions if int(q["question_number"]) not in answered_nums]

    if not remaining:
        await db.table("sessions").update(
            {"ended_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(session_id)).execute()
        return AnswerOut(done=True, session_id=session_id, predicted_level=predicted_level, confidence=confidence)

    candidate_nums = [int(q["question_number"]) for q in remaining]
    candidate_diffs = [q.get("difficulty") for q in remaining]
    next_num = ml_service.select_next_question(features, candidate_nums, candidate_diffs, strategy="entropy")
    next_question = next((q for q in remaining if int(q["question_number"]) == next_num), remaining[0])

    return AnswerOut(
        done=False,
        question=_serialize_question(next_question),
        question_number=int(next_question["question_number"]),
        total=total,
        predicted_level=predicted_level,
        confidence=confidence,
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

    questions_resp = (
        await db.table("questions")
        .select("*")
        .eq("quiz_id", session["quiz_id"])
        .execute()
    )
    questions_by_number = {int(q["question_number"]): q for q in (questions_resp.data or [])}

    total = len(answers)
    correct = sum(1 for a in answers if a.get("is_correct"))
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

        chosen = answer["chosen_answer"]
        correct_ans = question["correct_answer"]
        by_question.append(
            QuestionResultOut(
                question_number=int(answer["question_number"]),
                question_text=question["question_text"],
                question_image_url=question.get("question_image_url"),
                chosen_answer=chosen,
                correct_answer=correct_ans,
                chosen_answer_text=_choice_text(question, chosen),
                chosen_answer_image_url=_choice_image_url(question, chosen),
                correct_answer_text=_choice_text(question, correct_ans) or correct_ans.upper(),
                correct_answer_image_url=_choice_image_url(question, correct_ans),
                is_correct=bool(answer.get("is_correct")),
                response_time_ms=int(answer["response_time_ms"]),
                difficulty=question.get("difficulty"),
                answered_at=answer["answered_at"],
            )
        )

    by_difficulty = {
        key: {
            "total": val["total"],
            "correct": val["correct"],
            "accuracy": (val["correct"] / val["total"]) if val["total"] else 0.0,
        }
        for key, val in by_difficulty_raw.items()
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
        .select("*")
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
    answers_resp = (
        await db.table("answers")
        .select("session_id,is_correct")
        .in_("session_id", session_ids)
        .execute()
    )
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
        t = int(totals.get(sid, 0))
        c = int(corrects.get(sid, 0))
        history.append(
            SessionHistoryOut(
                session_id=sid,
                quiz_id=row["quiz_id"],
                display_name=quiz_name_by_id.get(row["quiz_id"], row["quiz_id"]),
                started_at=row["started_at"],
                ended_at=row.get("ended_at"),
                total=t,
                correct=c,
                accuracy=(c / t) if t else 0.0,
                is_adaptive=bool(row.get("is_adaptive", False)),
            )
        )
    return history
