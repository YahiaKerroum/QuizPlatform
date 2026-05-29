import csv
import io
import json
import re
from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, status
from postgrest import AsyncPostgrestClient

from ..schemas import ImportOut

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}
CHOICE_ORDER = ["choice_a", "choice_b", "choice_c", "choice_d", "choice_e", "choice_f"]
CHOICE_IMAGE_ORDER = [
    "choice_a_image_url",
    "choice_b_image_url",
    "choice_c_image_url",
    "choice_d_image_url",
    "choice_e_image_url",
    "choice_f_image_url",
]


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


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
    module_id = _pick_value(row, "module_id")
    module_name = _pick_value(row, "module_name", "module_display_name", "module")

    if not quiz_id or question_number is None or not question_text or not correct_answer or not topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Import rows must include quiz_id, a question number column, question text, correct, and topic/display_name.",
        )

    normalized = {
        "quiz_id": str(quiz_id).strip(),
        "question_number": int(question_number),
        "question_text": str(question_text).strip(),
        "question_image_url": _pick_value(row, "question_image_url", "question_image", "image_url"),
        "module_id": _slugify(str(module_id)) if module_id else (_slugify(str(module_name)) if module_name else None),
        "module_name": str(module_name).strip() if module_name else None,
        "choice_a": str(_pick_value(row, "choice_a") or "").strip(),
        "choice_a_image_url": _pick_value(row, "choice_a_image_url", "choice_a_image"),
        "choice_b": str(_pick_value(row, "choice_b") or "").strip(),
        "choice_b_image_url": _pick_value(row, "choice_b_image_url", "choice_b_image"),
        "choice_c": _pick_value(row, "choice_c"),
        "choice_c_image_url": _pick_value(row, "choice_c_image_url", "choice_c_image"),
        "choice_d": _pick_value(row, "choice_d"),
        "choice_d_image_url": _pick_value(row, "choice_d_image_url", "choice_d_image"),
        "choice_e": _pick_value(row, "choice_e"),
        "choice_e_image_url": _pick_value(row, "choice_e_image_url", "choice_e_image"),
        "choice_f": _pick_value(row, "choice_f"),
        "choice_f_image_url": _pick_value(row, "choice_f_image_url", "choice_f_image"),
        "correct_answer": str(correct_answer).strip().lower(),
        "topic": str(topic).strip(),
    }

    for optional_key in ("question_image_url", "module_name", "choice_c", "choice_d", "choice_e", "choice_f", *CHOICE_IMAGE_ORDER):
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
            module_id = _pick_value(quiz, "module_id")
            module_name = _pick_value(quiz, "module_name", "module_display_name", "module")
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
                            "module_id": module_id,
                            "module_name": module_name,
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


async def process_import(db: AsyncPostgrestClient, rows: list[dict[str, Any]]) -> ImportOut:
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rows were provided for import.",
        )

    quizzes_by_id: dict[str, str] = {}
    quiz_modules_by_id: dict[str, str | None] = {}
    modules_by_id: dict[str, str | None] = {}
    for row in rows:
        quizzes_by_id.setdefault(row["quiz_id"], row["topic"])
        quiz_modules_by_id.setdefault(row["quiz_id"], row["module_id"])
        if row["module_id"]:
            modules_by_id.setdefault(row["module_id"], row["module_name"] or row["module_id"])

    if modules_by_id:
        module_stmt = (
            insert(Module)
            .values(
                [
                    {
                        "id": module_id,
                        "display_name": module_name or module_id,
                    }
                    for module_id, module_name in modules_by_id.items()
                ]
            )
            .on_conflict_do_nothing(index_elements=[Module.id])
        )
        await db.execute(module_stmt)

    quiz_stmt = (
        insert(Quiz)
        .values(
            [
                {
                    "id": quiz_id,
                    "display_name": topic,
                    "module_id": quiz_modules_by_id.get(quiz_id),
                }
                for quiz_id, topic in quizzes_by_id.items()
            ]
        )
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
                    "question_image_url": row["question_image_url"],
                    "choice_a": row["choice_a"],
                    "choice_a_image_url": row["choice_a_image_url"],
                    "choice_b": row["choice_b"],
                    "choice_b_image_url": row["choice_b_image_url"],
                    "choice_c": row["choice_c"],
                    "choice_c_image_url": row["choice_c_image_url"],
                    "choice_d": row["choice_d"],
                    "choice_d_image_url": row["choice_d_image_url"],
                    "choice_e": row["choice_e"],
                    "choice_e_image_url": row["choice_e_image_url"],
                    "choice_f": row["choice_f"],
                    "choice_f_image_url": row["choice_f_image_url"],
                    "correct_answer": row["correct_answer"],
                    "difficulty": row.get("difficulty") or None,
                }
                for row in rows
            ]
        )
        existing_question_pairs = {
            (row["quiz_id"], int(row["question_number"]))
            for row in (existing_questions_resp.data or [])
        }

    question_rows = [
        {
            "quiz_id": row["quiz_id"],
            "question_number": row["question_number"],
            "question_text": row["question_text"],
            "question_image_url": row["question_image_url"],
            "choice_a": row["choice_a"],
            "choice_a_image_url": row["choice_a_image_url"],
            "choice_b": row["choice_b"],
            "choice_b_image_url": row["choice_b_image_url"],
            "choice_c": row["choice_c"],
            "choice_c_image_url": row["choice_c_image_url"],
            "choice_d": row["choice_d"],
            "choice_d_image_url": row["choice_d_image_url"],
            "choice_e": row["choice_e"],
            "choice_e_image_url": row["choice_e_image_url"],
            "choice_f": row["choice_f"],
            "choice_f_image_url": row["choice_f_image_url"],
            "correct_answer": row["correct_answer"],
            "difficulty": None,
        }
        for row in rows
        if (row["quiz_id"], int(row["question_number"])) not in existing_question_pairs
    ]

    if question_rows:
        await db.table("questions").insert(question_rows).execute()
    questions_inserted = len(question_rows)

    return ImportOut(
        quizzes_created=quizzes_created,
        questions_inserted=questions_inserted,
        questions_skipped=len(rows) - questions_inserted,
    )
