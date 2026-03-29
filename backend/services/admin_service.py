from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Answer, Question, Session, Student
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


async def create_synthetic_students(db: AsyncSession, payload: BulkStudentsIn) -> list[dict[str, object]]:
    if not payload.students:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one synthetic student email is required.",
        )

    stmt = (
        insert(Student)
        .values(
            [
                {
                    "email": item.email.lower().strip(),
                    "password_hash": None,
                    "is_synthetic": True,
                }
                for item in payload.students
            ]
        )
        .on_conflict_do_nothing(index_elements=[Student.email])
        .returning(Student.email, Student.id)
    )
    rows = (await db.execute(stmt)).all()
    return [{"email": row.email, "id": row.id} for row in rows]


async def simulate_batch(db: AsyncSession, payload: SimBatchIn) -> SimBatchOut:
    submitted_ids = {student.student_id for student in payload.students}
    if not submitted_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Simulation payload must include at least one student.",
        )

    valid_students_result = await db.execute(
        select(Student.id).where(
            Student.id.in_(submitted_ids),
            Student.is_synthetic.is_(True),
        )
    )
    valid_student_ids = set(valid_students_result.scalars().all())
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

    questions_result = await db.execute(
        select(
            Question.quiz_id,
            Question.question_number,
            Question.correct_answer,
        ).where(tuple_(Question.quiz_id, Question.question_number).in_(referenced_pairs))
    )
    question_rows = questions_result.all()
    question_lookup = {
        (row.quiz_id, row.question_number): row.correct_answer
        for row in question_rows
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
            session = Session(
                student_id=student.student_id,
                quiz_id=session_payload.quiz_id,
            )
            db.add(session)
            await db.flush()
            sessions_created += 1

            for answer_payload in session_payload.answers:
                chosen_answer = _normalize_choice(answer_payload.chosen_answer)
                correct_answer = question_lookup[(session_payload.quiz_id, answer_payload.question_number)]
                db.add(
                    Answer(
                        session_id=session.id,
                        quiz_id=session_payload.quiz_id,
                        question_number=answer_payload.question_number,
                        chosen_answer=chosen_answer,
                        is_correct=chosen_answer == correct_answer,
                        response_time_ms=answer_payload.response_time_ms,
                    )
                )
                answers_inserted += 1

            session.ended_at = datetime.now(timezone.utc)
            await db.flush()

    return SimBatchOut(
        sessions_created=sessions_created,
        answers_inserted=answers_inserted,
        errors=[],
    )


async def update_question_difficulties(db: AsyncSession, payload: DifficultyIn) -> DifficultyOut:
    updated = 0
    for item in payload.updates:
        difficulty = item.difficulty.strip().lower()
        if difficulty not in VALID_DIFFICULTIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="difficulty must be easy, medium, or hard.",
            )

        result = await db.execute(
            update(Question)
            .where(
                Question.quiz_id == item.quiz_id,
                Question.question_number == item.question_number,
            )
            .values(difficulty=difficulty)
        )
        updated += result.rowcount or 0

    return DifficultyOut(updated=updated)
