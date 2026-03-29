from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import BulkStudentsIn, DifficultyIn, DifficultyOut, ImportOut, SimBatchIn, SimBatchOut, SyntheticStudentOut
from ..services.admin_service import create_synthetic_students, simulate_batch, update_question_difficulties
from ..services.export_service import stream_answers_csv
from ..services.import_service import parse_csv, parse_json, process_import

router = APIRouter()


@router.post("/import", response_model=ImportOut)
async def import_questions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> ImportOut:
    content = await file.read()
    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    if filename.endswith(".csv") or content_type == "text/csv":
        rows = parse_csv(content)
    elif filename.endswith(".json") or content_type == "application/json":
        rows = parse_json(content)
    else:
        try:
            rows = parse_json(content)
        except HTTPException as json_error:
            try:
                rows = parse_csv(content)
            except HTTPException:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported import file. Upload CSV or JSON.",
                ) from json_error

    return await process_import(db, rows)


@router.post("/students/synthetic/bulk", response_model=list[SyntheticStudentOut])
async def bulk_create_synthetic_students(
    payload: BulkStudentsIn,
    db: AsyncSession = Depends(get_db),
) -> list[SyntheticStudentOut]:
    created = await create_synthetic_students(db, payload)
    return [SyntheticStudentOut.model_validate(item) for item in created]


@router.post("/simulate/batch", response_model=SimBatchOut)
async def run_simulation_batch(
    payload: SimBatchIn,
    db: AsyncSession = Depends(get_db),
) -> SimBatchOut:
    return await simulate_batch(db, payload)


@router.post("/questions/difficulty", response_model=DifficultyOut)
async def set_question_difficulty(
    payload: DifficultyIn,
    db: AsyncSession = Depends(get_db),
) -> DifficultyOut:
    return await update_question_difficulties(db, payload)


@router.get("/export/answers")
async def export_answers() -> StreamingResponse:
    return StreamingResponse(
        stream_answers_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="responses.csv"'},
    )
