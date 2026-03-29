import csv
import io
import json
from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Question, Quiz
from ..schemas import ImportOut

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}
CHOICE_ORDER = ["choice_a", "choice_b", "choice_c", "choice_d", "choice_e", "choice_f"]


def _pick_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue
        return value
    return None


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    quiz_id = _pick_value(row, "quiz_id")
    question_number = _pick_value(row, "question_number", "question_id", "question_no", "questionNumber")
    question_text = _pick_value(row, "question_text", "question", "text")
    correct_answer = _pick_value(row, "correct_answer", "correct")
    topic = _pick_value(row, "topic", "display_name")

    if not quiz_id or question_number is None or not question_text or not correct_answer or not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import rows must include quiz_id, a question number column, question text, correct, and topic/display_name.",
        )

    normalized = {
        "quiz_id": str(quiz_id).strip(),
        "question_number": int(question_number),
        "question_text": str(question_text).strip(),
        "choice_a": str(_pick_value(row, "choice_a") or "").strip(),
        "choice_b": str(_pick_value(row, "choice_b") or "").strip(),
        "choice_c": _pick_value(row, "choice_c"),
        "choice_d": _pick_value(row, "choice_d"),
        "choice_e": _pick_value(row, "choice_e"),
        "choice_f": _pick_value(row, "choice_f"),
        "correct_answer": str(correct_answer).strip().lower(),
        "topic": str(topic).strip(),
    }

    for optional_key in ("choice_c", "choice_d", "choice_e", "choice_f"):
        value = normalized[optional_key]
        if isinstance(value, str):
            value = value.strip() or None
        normalized[optional_key] = value

    if not all(normalized[key] for key in ("choice_a", "choice_b")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each imported question must include choices a and b.",
        )

    if normalized["correct_answer"] not in VALID_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correct/correct_answer must be one of a, b, c, d, e, or f.",
        )

    required_choice_index = ord(normalized["correct_answer"]) - ord("a")
    required_choice_key = CHOICE_ORDER[required_choice_index]
    if not normalized.get(required_choice_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"correct_answer '{normalized['correct_answer']}' does not have a corresponding non-null choice.",
        )

    return normalized


def parse_csv(content: bytes) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is missing headers.",
        )

    rows = [_normalize_row(dict(row)) for row in reader]
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import file contains no rows.",
        )
    return rows


def parse_json(content: bytes) -> list[dict[str, Any]]:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc

    if not isinstance(data, list) or not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON import must be a non-empty array.",
        )

    if isinstance(data[0], dict) and "questions" in data[0]:
        rows: list[dict[str, Any]] = []
        for quiz in data:
            quiz_id = _pick_value(quiz, "quiz_id")
            topic = _pick_value(quiz, "display_name", "topic", "quiz_id")
            questions = quiz.get("questions")
            if not quiz_id or not isinstance(questions, Iterable):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nested JSON import entries must include quiz_id and questions.",
                )
            for question in questions:
                rows.append(
                    _normalize_row(
                        {
                            **question,
                            "quiz_id": quiz_id,
                            "topic": topic,
                        }
                    )
                )
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON import contains no questions.",
            )
        return rows

    return [_normalize_row(dict(row)) for row in data]


async def process_import(db: AsyncSession, rows: list[dict[str, Any]]) -> ImportOut:
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rows were provided for import.",
        )

    quizzes_by_id: dict[str, str] = {}
    for row in rows:
        quizzes_by_id.setdefault(row["quiz_id"], row["topic"])

    quiz_stmt = (
        insert(Quiz)
        .values([{"id": quiz_id, "display_name": topic} for quiz_id, topic in quizzes_by_id.items()])
        .on_conflict_do_nothing(index_elements=[Quiz.id])
        .returning(Quiz.id)
    )
    quizzes_created = len((await db.execute(quiz_stmt)).scalars().all())

    question_stmt = (
        insert(Question)
        .values(
            [
                {
                    "quiz_id": row["quiz_id"],
                    "question_number": row["question_number"],
                    "question_text": row["question_text"],
                    "choice_a": row["choice_a"],
                    "choice_b": row["choice_b"],
                    "choice_c": row["choice_c"],
                    "choice_d": row["choice_d"],
                    "choice_e": row["choice_e"],
                    "choice_f": row["choice_f"],
                    "correct_answer": row["correct_answer"],
                    "difficulty": None,
                }
                for row in rows
            ]
        )
        .on_conflict_do_nothing(index_elements=[Question.quiz_id, Question.question_number])
        .returning(Question.quiz_id, Question.question_number)
    )
    questions_inserted = len((await db.execute(question_stmt)).all())

    return ImportOut(
        quizzes_created=quizzes_created,
        questions_inserted=questions_inserted,
        questions_skipped=len(rows) - questions_inserted,
    )
