import csv
import io
from collections.abc import AsyncGenerator

from sqlalchemy import and_, select

from ..database import AsyncSessionLocal
from ..models import Answer, Question, Quiz, Session, Student


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

    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                Student.id,
                Answer.quiz_id,
                Answer.question_number,
                Question.question_text,
                Quiz.display_name,
                Question.difficulty,
                Answer.chosen_answer,
                Answer.is_correct,
                Answer.response_time_ms,
                Student.is_synthetic,
                Answer.answered_at,
            )
            .join(Session, Session.id == Answer.session_id)
            .join(Student, Student.id == Session.student_id)
            .join(
                Question,
                and_(
                    Question.quiz_id == Answer.quiz_id,
                    Question.question_number == Answer.question_number,
                ),
            )
            .join(Quiz, Quiz.id == Answer.quiz_id)
            .order_by(Answer.answered_at.asc(), Answer.quiz_id.asc(), Answer.question_number.asc())
        )

        stream = await session.stream(stmt)
        async for row in stream:
            yield _csv_row(
                [
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                ]
            )

