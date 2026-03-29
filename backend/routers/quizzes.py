from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Question, Quiz
from ..schemas import QuestionOut, QuizDetailOut, QuizSummaryOut

router = APIRouter()


@router.get("", response_model=list[QuizSummaryOut])
async def list_quizzes(db: AsyncSession = Depends(get_db)) -> list[QuizSummaryOut]:
    result = await db.execute(
        select(
            Quiz.id,
            Quiz.display_name,
            func.count(Question.question_number).label("question_count"),
        )
        .outerjoin(Question, Question.quiz_id == Quiz.id)
        .group_by(Quiz.id, Quiz.display_name)
        .order_by(Quiz.display_name.asc())
    )
    return [
        QuizSummaryOut(
            id=row.id,
            display_name=row.display_name,
            question_count=row.question_count,
        )
        for row in result.all()
    ]


@router.get("/{quiz_id}", response_model=QuizDetailOut)
async def get_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)) -> QuizDetailOut:
    result = await db.execute(
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.id == quiz_id)
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found.")

    return QuizDetailOut(
        id=quiz.id,
        display_name=quiz.display_name,
        questions=[QuestionOut.model_validate(question) for question in quiz.questions],
    )
