from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models import Student
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register_student(payload: RegisterIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    existing = await db.execute(select(Student).where(Student.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    student = Student(
        email=email,
        password_hash=hash_password(payload.password),
        is_synthetic=False,
    )
    db.add(student)
    await db.flush()

    return TokenOut(
        access_token=create_access_token(student.id),
        student_id=student.id,
    )


@router.post("/login", response_model=TokenOut)
async def login_student(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()

    if (
        student is None
        or student.is_synthetic
        or student.password_hash is None
        or not verify_password(payload.password, student.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return TokenOut(
        access_token=create_access_token(student.id),
        student_id=student.id,
    )

