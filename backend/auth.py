from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest import AsyncPostgrestClient

from .database import get_db
from .supabase_auth import get_user_from_token

load_dotenv(Path(__file__).resolve().parent / ".env")
bearer_scheme = HTTPBearer(auto_error=False)


ADMIN_ALLOWED_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_ALLOWED_EMAILS", "").split(",")
    if email.strip()
}

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
bearer_scheme = HTTPBearer(auto_error=False)


async def _get_profile_by_email(email: str, db: AsyncPostgrestClient) -> dict | None:
    result = await db.table("profiles").select("*").eq("email", email).maybe_single().execute()
    return result.data if result is not None else None


def _parse_uuid(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def create_access_token(student_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(student_id),
        "role": "student",
        "exp": expires_at,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    user_id = _parse_uuid(user_data.get("id"))
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

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
        )
    return email


async def _get_user_data(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
        )

    try:
        return get_user_from_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc


async def get_current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncPostgrestClient = Depends(get_db),
) -> dict:
    user_data = await _get_user_data(credentials)
    email = _extract_email(user_data)
    student = await _resolve_student_by_email(email, db)
    if bool(student.get("is_synthetic")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Synthetic users cannot access this route.",
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
