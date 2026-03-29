from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import ModuleWithQuizzesOut, QuizDetailOut, QuizSummaryOut
from ..services.catalog_service import (
    get_quiz_detail,
    list_modules_with_quizzes,
    list_quizzes as list_quiz_summaries,
)

router = APIRouter()


@router.get("", response_model=list[QuizSummaryOut])
async def list_quizzes(db: AsyncSession = Depends(get_db)) -> list[QuizSummaryOut]:
    return await list_quiz_summaries(db)


@router.get("/modules", response_model=list[ModuleWithQuizzesOut])
async def list_quiz_modules(db: AsyncSession = Depends(get_db)) -> list[ModuleWithQuizzesOut]:
    return await list_modules_with_quizzes(db)


@router.get("/{quiz_id}", response_model=QuizDetailOut)
async def get_quiz(quiz_id: str, db: AsyncSession = Depends(get_db)) -> QuizDetailOut:
    return await get_quiz_detail(db, quiz_id)
