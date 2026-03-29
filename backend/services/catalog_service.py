import re

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Answer, Module, Question, Quiz
from ..schemas import (
    AdminQuizDetailOut,
    AdminQuestionIn,
    ModuleCreateIn,
    ModuleOut,
    ModuleUpdateIn,
    ModuleWithQuizzesOut,
    QuestionOut,
    QuizDetailOut,
    QuizSummaryOut,
    QuizUpsertIn,
)

VALID_CHOICES = {"a", "b", "c", "d", "e", "f"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
CHOICE_KEYS = ["choice_a", "choice_b", "choice_c", "choice_d", "choice_e", "choice_f"]
IMAGE_KEYS = [
    "choice_a_image_url",
    "choice_b_image_url",
    "choice_c_image_url",
    "choice_d_image_url",
    "choice_e_image_url",
    "choice_f_image_url",
]


def _normalize_module_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _serialize_quiz_summary(
    quiz_id: str,
    display_name: str,
    question_count: int,
    module_id: str | None,
    module_display_name: str | None,
) -> QuizSummaryOut:
    return QuizSummaryOut(
        id=quiz_id,
        display_name=display_name,
        module_id=module_id,
        module_display_name=module_display_name,
        question_count=int(question_count),
    )


def _serialize_quiz_detail(quiz: Quiz) -> QuizDetailOut:
    module = quiz.module
    return QuizDetailOut(
        id=quiz.id,
        display_name=quiz.display_name,
        module_id=module.id if module else None,
        module_display_name=module.display_name if module else None,
        questions=[QuestionOut.model_validate(question) for question in quiz.questions],
    )


def _serialize_admin_quiz_detail(quiz: Quiz) -> AdminQuizDetailOut:
    module = quiz.module
    return AdminQuizDetailOut(
        id=quiz.id,
        display_name=quiz.display_name,
        module_id=module.id if module else None,
        module_display_name=module.display_name if module else None,
        questions=[
            AdminQuestionIn(
                question_number=question.question_number,
                question_text=question.question_text,
                question_image_url=question.question_image_url,
                choice_a=question.choice_a,
                choice_a_image_url=question.choice_a_image_url,
                choice_b=question.choice_b,
                choice_b_image_url=question.choice_b_image_url,
                choice_c=question.choice_c,
                choice_c_image_url=question.choice_c_image_url,
                choice_d=question.choice_d,
                choice_d_image_url=question.choice_d_image_url,
                choice_e=question.choice_e,
                choice_e_image_url=question.choice_e_image_url,
                choice_f=question.choice_f,
                choice_f_image_url=question.choice_f_image_url,
                correct_answer=question.correct_answer,
                difficulty=question.difficulty,
            )
            for question in quiz.questions
        ],
    )


def _normalize_question_payload(question: AdminQuestionIn) -> dict[str, str | int | None]:
    normalized = question.model_dump()
    normalized["question_text"] = question.question_text.strip()
    normalized["question_image_url"] = _clean_optional(question.question_image_url)
    normalized["correct_answer"] = question.correct_answer.strip().lower()
    normalized["difficulty"] = _clean_optional(question.difficulty)

    for key in [*CHOICE_KEYS, *IMAGE_KEYS]:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = value.strip() or None

    if not normalized["question_text"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Every question must include question_text.",
        )

    if not normalized["choice_a"] or not normalized["choice_b"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each question must include choices a and b.",
        )

    if normalized["correct_answer"] not in VALID_CHOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correct_answer must be one of a, b, c, d, e, or f.",
        )

    difficulty = normalized["difficulty"]
    if difficulty is not None and difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="difficulty must be easy, medium, hard, or null.",
        )

    required_choice_key = f"choice_{normalized['correct_answer']}"
    if not normalized.get(required_choice_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"correct_answer '{normalized['correct_answer']}' must point to a non-empty choice.",
        )

    return normalized


def _normalize_quiz_payload(payload: QuizUpsertIn) -> tuple[str, str, str | None, list[dict[str, str | int | None]]]:
    quiz_id = payload.id.strip()
    display_name = payload.display_name.strip()
    module_id = _clean_optional(payload.module_id)

    if not quiz_id or not display_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz id and display_name are required.",
        )

    seen_numbers: set[int] = set()
    questions: list[dict[str, str | int | None]] = []

    for question in payload.questions:
        if question.question_number in seen_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate question_number {question.question_number} in quiz payload.",
            )
        seen_numbers.add(question.question_number)
        questions.append(_normalize_question_payload(question))

    ordered_numbers = sorted(seen_numbers)
    expected = list(range(1, len(ordered_numbers) + 1))
    if ordered_numbers != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz questions must be numbered contiguously starting at 1.",
        )

    return quiz_id, display_name, module_id, questions


async def _require_module(db: AsyncSession, module_id: str) -> Module:
    module = await db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    return module


async def list_modules(db: AsyncSession) -> list[ModuleOut]:
    result = await db.execute(
        select(
            Module.id,
            Module.display_name,
            Module.description,
            func.count(Quiz.id).label("quiz_count"),
        )
        .outerjoin(Quiz, Quiz.module_id == Module.id)
        .group_by(Module.id, Module.display_name, Module.description)
        .order_by(Module.display_name.asc())
    )
    return [
        ModuleOut(
            id=row.id,
            display_name=row.display_name,
            description=row.description,
            quiz_count=int(row.quiz_count or 0),
        )
        for row in result.all()
    ]


async def create_module(db: AsyncSession, payload: ModuleCreateIn) -> ModuleOut:
    module_id = _normalize_module_id(payload.id)
    if not module_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module id is invalid.")

    existing = await db.get(Module, module_id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module id already exists.")

    module = Module(
        id=module_id,
        display_name=payload.display_name.strip(),
        description=_clean_optional(payload.description),
    )
    db.add(module)
    await db.flush()
    return ModuleOut(id=module.id, display_name=module.display_name, description=module.description, quiz_count=0)


async def update_module(db: AsyncSession, module_id: str, payload: ModuleUpdateIn) -> ModuleOut:
    module = await db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")

    module.display_name = payload.display_name.strip()
    module.description = _clean_optional(payload.description)
    await db.flush()

    quiz_count = await db.scalar(select(func.count()).select_from(Quiz).where(Quiz.module_id == module.id))
    return ModuleOut(
        id=module.id,
        display_name=module.display_name,
        description=module.description,
        quiz_count=int(quiz_count or 0),
    )


async def list_quizzes(db: AsyncSession) -> list[QuizSummaryOut]:
    result = await db.execute(
        select(
            Quiz.id,
            Quiz.display_name,
            Quiz.module_id,
            Module.display_name.label("module_display_name"),
            func.count(Question.question_number).label("question_count"),
        )
        .outerjoin(Question, Question.quiz_id == Quiz.id)
        .outerjoin(Module, Module.id == Quiz.module_id)
        .group_by(Quiz.id, Quiz.display_name, Quiz.module_id, Module.display_name)
        .order_by(Module.display_name.asc().nullslast(), Quiz.display_name.asc())
    )
    return [
        _serialize_quiz_summary(
            row.id,
            row.display_name,
            row.question_count,
            row.module_id,
            row.module_display_name,
        )
        for row in result.all()
    ]


async def list_modules_with_quizzes(db: AsyncSession) -> list[ModuleWithQuizzesOut]:
    modules = await list_modules(db)
    quizzes = await list_quizzes(db)

    grouped: dict[str, list[QuizSummaryOut]] = {module.id: [] for module in modules}
    ungrouped: list[QuizSummaryOut] = []

    for quiz in quizzes:
        if quiz.module_id and quiz.module_id in grouped:
            grouped[quiz.module_id].append(quiz)
        else:
            ungrouped.append(quiz)

    payload = [
        ModuleWithQuizzesOut(
            id=module.id,
            display_name=module.display_name,
            description=module.description,
            quizzes=grouped[module.id],
        )
        for module in modules
    ]

    if ungrouped:
        payload.append(
            ModuleWithQuizzesOut(
                id="ungrouped",
                display_name="Ungrouped",
                description="Quizzes not assigned to a module yet.",
                quizzes=ungrouped,
            )
        )

    return payload


async def get_quiz_detail(db: AsyncSession, quiz_id: str) -> QuizDetailOut:
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions), selectinload(Quiz.module))
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    return _serialize_quiz_detail(quiz)


async def get_admin_quiz_detail(db: AsyncSession, quiz_id: str) -> AdminQuizDetailOut:
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions), selectinload(Quiz.module))
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")
    return _serialize_admin_quiz_detail(quiz)


async def create_quiz(db: AsyncSession, payload: QuizUpsertIn) -> AdminQuizDetailOut:
    quiz_id, display_name, module_id, questions = _normalize_quiz_payload(payload)

    existing = await db.get(Quiz, quiz_id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz id already exists.")

    if module_id:
        await _require_module(db, module_id)

    quiz = Quiz(id=quiz_id, display_name=display_name, module_id=module_id)
    db.add(quiz)
    await db.flush()

    for question in questions:
        db.add(Question(quiz_id=quiz.id, **question))

    await db.flush()
    return await get_admin_quiz_detail(db, quiz.id)


async def update_quiz(db: AsyncSession, quiz_id: str, payload: QuizUpsertIn) -> AdminQuizDetailOut:
    normalized_id, display_name, module_id, questions = _normalize_quiz_payload(payload)
    if normalized_id != quiz_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quiz id in the body must match the URL.",
        )

    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions), selectinload(Quiz.module))
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    if module_id:
        await _require_module(db, module_id)

    answers_count = await db.scalar(select(func.count()).select_from(Answer).where(Answer.quiz_id == quiz_id))
    existing_by_number = {question.question_number: question for question in quiz.questions}
    incoming_numbers = {int(question["question_number"]) for question in questions}
    existing_numbers = set(existing_by_number)

    if answers_count and incoming_numbers != existing_numbers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This quiz already has answer history, so you can only edit existing question content, not add or remove question numbers.",
        )

    quiz.display_name = display_name
    quiz.module_id = module_id

    for question_payload in questions:
        question_number = int(question_payload["question_number"])
        question = existing_by_number.get(question_number)
        if question is None:
            db.add(Question(quiz_id=quiz.id, **question_payload))
            continue

        for key, value in question_payload.items():
            setattr(question, key, value)

    if not answers_count:
        removable_numbers = existing_numbers - incoming_numbers
        if removable_numbers:
            await db.execute(
                delete(Question).where(
                    Question.quiz_id == quiz_id,
                    Question.question_number.in_(removable_numbers),
                )
            )

    await db.flush()
    return await get_admin_quiz_detail(db, quiz.id)
