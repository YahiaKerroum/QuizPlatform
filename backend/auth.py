import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest import AsyncPostgrestClient

from .database import get_admin_db, get_user_db
from .supabase_auth import get_user_from_token

load_dotenv(Path(__file__).resolve().parent / ".env")

ADMIN_ALLOWED_EMAILS = {
    email.strip().lower()
    for email in os.getenv("ADMIN_ALLOWED_EMAILS", "").split(",")
    if email.strip()
}

bearer_scheme = HTTPBearer(auto_error=False)


def is_admin_email(email: str) -> bool:
    return email.strip().lower() in ADMIN_ALLOWED_EMAILS


def _extract_email(user_data: dict) -> str:
    email = user_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )
    return email


async def _ensure_profile(user_id: str, email: str, db: AsyncPostgrestClient) -> None:
    existing = await db.table("profiles").select("user_id").eq("user_id", user_id).maybe_single().execute()
    if existing is None or existing.data is None:
        await db.table("profiles").insert({
            "user_id": user_id,
            "email": email.lower().strip(),
            "role": "student",
        }).execute()


async def _resolve_student_by_email(user_data: dict, db: AsyncPostgrestClient) -> dict:
    """Resolve the student row for an authenticated user, provisioning it on first
    access. The frontend authenticates directly with Supabase, so a valid token may
    arrive before any student/profile row exists — create it lazily here."""
    email = _extract_email(user_data)
    result = await db.table("students").select("*").eq("email", email).maybe_single().execute()
    if result is not None and result.data is not None:
        return result.data

    user_id = user_data.get("id")
    if user_id:
        await _ensure_profile(user_id, email, db)
    insert = await db.table("students").insert({
        "email": email.lower().strip(),
        "password_hash": None,
        "is_synthetic": False,
    }).execute()
    student = insert.data[0] if insert and insert.data else None
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not provision student record.",
        )
    return student


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
) -> dict:
    user_data = await _get_user_data(credentials)
    # Student lookup always uses the service-role client (system operation).
    db = get_admin_db()
    student = await _resolve_student_by_email(user_data, db)
    if bool(student.get("is_synthetic")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Synthetic users cannot access this route.",
        )
    return student


async def get_student_db(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AsyncPostgrestClient:
    """Returns a PostgREST client scoped to the user's JWT so RLS is enforced."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
        )
    return get_user_db(credentials.credentials)


def require_admin(
    student: dict = Depends(get_current_student),
) -> dict:
    if not ADMIN_ALLOWED_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is not configured.",
        )
    if not is_admin_email(student["email"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not allowed to access the admin portal.",
        )
    return student
