import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import Student

load_dotenv(Path(__file__).resolve().parent / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set.")

ADMIN_ALLOWED_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_ALLOWED_EMAILS", "").split(",")
    if email.strip()
}

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(student_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(student_id),
        "role": "student",
        "exp": expires_at,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in ADMIN_ALLOWED_EMAILS


def verify_token(token: str) -> UUID:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "student":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            )
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
            )
        return UUID(subject)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc


async def get_current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Student:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
        )

    student_id = verify_token(credentials.credentials)
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student not found.",
        )
    return student


def require_admin(
    student: Student = Depends(get_current_student),
) -> Student:
    if not ADMIN_ALLOWED_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is not configured.",
        )

    if not is_admin_email(student.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not allowed to access the admin portal.",
        )

    return student
