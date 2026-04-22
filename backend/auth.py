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


async def _resolve_student_by_email(email: str, db: AsyncPostgrestClient) -> dict:
    result = await db.table("students").select("*").eq("email", email).maybe_single().execute()
    student = result.data if result is not None else None
    if student is None:
        insert_result = (
            await db.table("students")
            .insert(
                {
                    "email": email,
                    "password_hash": None,
                    "is_synthetic": False,
                }
            )
            .execute()
        )
        student = insert_result.data[0] if insert_result is not None and insert_result.data else None
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load student record.",
        )
    return student


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


async def ensure_profile_for_user(user_data: dict, db: AsyncPostgrestClient) -> dict:
    email = _extract_email(user_data)
    profile = await _get_profile_by_email(email, db)
    if profile is not None:
        return profile

    user_id = _parse_uuid(user_data.get("id"))
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    insert_result = (
        await db.table("profiles")
        .insert(
            {
                "user_id": str(user_id),
                "email": email,
                "role": "student",
            }
        )
        .execute()
    )
    if insert_result is None or not insert_result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create profile record.",
        )
    return insert_result.data[0]


def _extract_email(user_data: dict) -> str:
    email = str(user_data.get("email") or "").lower().strip()
    if not email:
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


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncPostgrestClient = Depends(get_db),
) -> dict:
    user_data = await _get_user_data(credentials)
    profile = await ensure_profile_for_user(user_data, db)
    if profile.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access admin routes.",
        )

    return user_data


async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncPostgrestClient = Depends(get_db),
) -> dict:
    user_data = await _get_user_data(credentials)
    profile = await ensure_profile_for_user(user_data, db)
    return {
        "email": profile["email"],
        "is_admin": profile.get("role") == "admin",
    }
