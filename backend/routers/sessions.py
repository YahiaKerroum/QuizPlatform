from uuid import UUID

from fastapi import APIRouter, Depends
from postgrest import AsyncPostgrestClient

from ..auth import get_current_student
from ..database import get_db
from ..schemas import AnswerIn, AnswerOut, ResultOut, SessionHistoryOut, SessionStartIn, SessionStartOut
from ..services.session_service import create_session, get_result, list_session_history, submit_answer

router = APIRouter()


@router.post("", response_model=SessionStartOut)
async def start_session(
    payload: SessionStartIn,
    db: AsyncPostgrestClient = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> SessionStartOut:
    return await create_session(db, current_student, payload.quiz_id, payload.adaptive)


@router.post("/{session_id}/answers", response_model=AnswerOut)
async def answer_question(
    session_id: UUID,
    payload: AnswerIn,
    db: AsyncPostgrestClient = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> AnswerOut:
    return await submit_answer(db, session_id, current_student, payload)


@router.get("/{session_id}/result", response_model=ResultOut)
async def session_result(
    session_id: UUID,
    db: AsyncPostgrestClient = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> ResultOut:
    return await get_result(db, session_id, current_student)


@router.get("/history", response_model=list[SessionHistoryOut])
async def session_history(
    db: AsyncPostgrestClient = Depends(get_db),
    current_student: dict = Depends(get_current_student),
) -> list[SessionHistoryOut]:
    return await list_session_history(db, current_student)
