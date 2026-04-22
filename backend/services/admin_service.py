from datetime import datetime, timezone

from fastapi import HTTPException, status
from postgrest import AsyncPostgrestClient

from ..schemas import BulkStudentsIn, DifficultyIn, DifficultyOut, SimBatchIn, SimBatchOut

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _normalize_choice(choice: str) -> str:
    normalized = choice.strip().lower()
    if normalized not in VALID_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chosen_answer must be one of a, b, c, d, e, or f.",
        )
    return normalized


async def create_synthetic_students(db: AsyncPostgrestClient, payload: BulkStudentsIn) -> list[dict[str, object]]:
    if not payload.students:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one synthetic student email is required.",
        )

    students_data = [
        {
            "email": item.email.lower().strip(),
            "password_hash": None,
            "is_synthetic": True,
        }
        for item in payload.students
    ]
    
    # Supabase postgrest-py doesn't have a direct on_conflict_do_nothing method on insert,
    # but we can use upsert with onConflict parameter.
    response = await db.table("students").upsert(students_data, on_conflict="email", ignore_duplicates=True).execute()
    # Actually wait, ignore_duplicates on upsert is available.
    
    # Return what was actually inserted, we might need to fetch the IDs
    emails = [item.email.lower().strip() for item in payload.students]
    inserted_students = await db.table("students").select("id, email").in_("email", emails).execute()
    
    return [{"email": row["email"], "id": row["id"]} for row in inserted_students.data]


async def simulate_batch(db: AsyncPostgrestClient, payload: SimBatchIn) -> SimBatchOut:
    submitted_ids = {str(student.student_id) for student in payload.students}
    if not submitted_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation payload must include at least one student.",
        )

    valid_students_result = await db.table("students").select("id").in_("id", list(submitted_ids)).eq("is_synthetic", True).execute()
    valid_student_ids = {str(row["id"]) for row in valid_students_result.data}
    unknown_ids = sorted(str(student_id) for student_id in submitted_ids - valid_student_ids)
    if unknown_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"unknown_student_ids": unknown_ids},
        )

    referenced_pairs = {
        (session.quiz_id, answer.question_number)
        for student in payload.students
        for session in student.sessions
        for answer in session.answers
    }
    if not referenced_pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation payload must include at least one answer.",
        )

    # Need to fetch questions for all quiz_ids and filter by question_numbers
    quiz_ids = list({pair[0] for pair in referenced_pairs})
    questions_result = await db.table("questions").select("quiz_id, question_number, correct_answer").in_("quiz_id", quiz_ids).execute()
    
    question_lookup = {
        (row["quiz_id"], row["question_number"]): row["correct_answer"]
        for row in questions_result.data
    }
    missing_pairs = sorted(
        (
            quiz_id,
            question_number,
        )
        for quiz_id, question_number in referenced_pairs
        if (quiz_id, question_number) not in question_lookup
    )
    unknown_pairs = [
        {
            "quiz_id": quiz_id,
            "question_number": question_number,
        }
        for quiz_id, question_number in missing_pairs
    ]
    if unknown_pairs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"unknown_questions": unknown_pairs},
        )

    sessions_created = 0
    answers_inserted = 0

    for student in payload.students:
        for session_payload in student.sessions:
            session_data = {
                "student_id": str(student.student_id),
                "quiz_id": session_payload.quiz_id,
            }
            # Insert session
            session_resp = await db.table("sessions").insert(session_data).execute()
            session = session_resp.data[0] if session_resp is not None and session_resp.data else None
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not create simulated session.",
                )
            session_id = session["id"]
            sessions_created += 1

            answers_data = []
            for answer_payload in session_payload.answers:
                chosen_answer = _normalize_choice(answer_payload.chosen_answer)
                correct_answer = question_lookup[(session_payload.quiz_id, answer_payload.question_number)]
                answers_data.append({
                    "session_id": session_id,
                    "quiz_id": session_payload.quiz_id,
                    "question_number": answer_payload.question_number,
                    "chosen_answer": chosen_answer,
                    "is_correct": chosen_answer == correct_answer,
                    "response_time_ms": answer_payload.response_time_ms,
                })
            
            if answers_data:
                await db.table("answers").insert(answers_data).execute()
                answers_inserted += len(answers_data)

            # Update ended_at
            await db.table("sessions").update({"ended_at": datetime.now(timezone.utc).isoformat()}).eq("id", session_id).execute()

    return SimBatchOut(
        sessions_created=sessions_created,
        answers_inserted=answers_inserted,
        errors=[],
    )


async def update_question_difficulties(db: AsyncPostgrestClient, payload: DifficultyIn) -> DifficultyOut:
    updated = 0
    for item in payload.updates:
        difficulty = item.difficulty.strip().lower()
        if difficulty not in VALID_DIFFICULTIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="difficulty must be easy, medium, or hard.",
            )

        result = await db.table("questions").update({"difficulty": difficulty}).eq("quiz_id", item.quiz_id).eq("question_number", item.question_number).execute()
        updated += len(result.data or [])

    return DifficultyOut(updated=updated)
