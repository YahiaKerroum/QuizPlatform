import csv
import io
from collections.abc import AsyncGenerator

from ..database import get_supabase_client


def _csv_row(values: list[object | None]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["" if value is None else value for value in values])
    return buffer.getvalue()


async def stream_answers_csv() -> AsyncGenerator[str, None]:
    header = [
        "student_id",
        "quiz_id",
        "question_number",
        "question_text",
        "topic",
        "difficulty",
        "chosen_answer",
        "is_correct",
        "response_time_ms",
        "is_synthetic",
        "answered_at",
    ]
    yield _csv_row(header)

    db = get_supabase_client()
    page_size = 1000
    offset = 0

    while True:
        answers_resp = (
            await db.table("answers")
            .select(
                "session_id,quiz_id,question_number,chosen_answer,is_correct,response_time_ms,answered_at"
            )
            .order("answered_at")
            .order("quiz_id")
            .order("question_number")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        answers = answers_resp.data or []
        if not answers:
            break

        session_ids = sorted({row["session_id"] for row in answers})
        quiz_ids = sorted({row["quiz_id"] for row in answers})

        sessions_resp = await db.table("sessions").select("id,student_id").in_("id", session_ids).execute()
        sessions = sessions_resp.data or []
        session_to_student = {row["id"]: row["student_id"] for row in sessions}

        student_ids = sorted({student_id for student_id in session_to_student.values() if student_id is not None})
        students_resp = await db.table("students").select("id,is_synthetic").in_("id", student_ids).execute()
        students = students_resp.data or []
        students_by_id = {row["id"]: row for row in students}

        quizzes_resp = await db.table("quizzes").select("id,display_name").in_("id", quiz_ids).execute()
        quizzes = quizzes_resp.data or []
        quiz_topic_by_id = {row["id"]: row["display_name"] for row in quizzes}

        questions_resp = (
            await db.table("questions")
            .select("quiz_id,question_number,question_text,difficulty")
            .in_("quiz_id", quiz_ids)
            .execute()
        )
        questions = questions_resp.data or []
        questions_by_key = {
            (row["quiz_id"], int(row["question_number"])): row for row in questions
        }

        for answer in answers:
            quiz_id = answer["quiz_id"]
            question_number = int(answer["question_number"])
            question = questions_by_key.get((quiz_id, question_number), {})

            student_id = session_to_student.get(answer["session_id"])
            student = students_by_id.get(student_id, {})

            yield _csv_row(
                [
                    student_id,
                    quiz_id,
                    question_number,
                    question.get("question_text"),
                    quiz_topic_by_id.get(quiz_id),
                    question.get("difficulty"),
                    answer.get("chosen_answer"),
                    answer.get("is_correct"),
                    answer.get("response_time_ms"),
                    student.get("is_synthetic"),
                    answer.get("answered_at"),
                ]
            )

        offset += page_size
