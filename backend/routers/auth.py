from fastapi import APIRouter, Depends, HTTPException, status
from postgrest import AsyncPostgrestClient

from ..auth import get_current_student, is_admin_email, require_admin
from ..database import get_db
from ..schemas import AdminAccessOut, LoginIn, RegisterIn, TokenOut
from ..supabase_auth import sign_in_with_password, sign_up_with_password

router = APIRouter()


async def _ensure_profile(user_id: str, email: str, db: AsyncPostgrestClient) -> None:
    existing = await db.table("profiles").select("user_id").eq("user_id", user_id).maybe_single().execute()
    if existing is None or existing.data is None:
        await db.table("profiles").insert({
            "user_id": user_id,
            "email": email.lower().strip(),
            "role": "student",
        }).execute()


async def _ensure_student(email: str, db: AsyncPostgrestClient) -> dict:
    result = await db.table("students").select("*").eq("email", email).maybe_single().execute()
    if result is not None and result.data is not None:
        return result.data
    insert = await db.table("students").insert({
        "email": email,
        "password_hash": None,
        "is_synthetic": False,
    }).execute()
    student = insert.data[0] if insert and insert.data else None
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create student record.",
        )
    return student


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register_student(payload: RegisterIn, db: AsyncPostgrestClient = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()

    existing = await db.table("students").select("id").eq("email", email).maybe_single().execute()
    if existing is not None and existing.data is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered.")

    try:
        auth_data = sign_up_with_password(email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await _ensure_profile(auth_data["id"], email, db)
    student = await _ensure_student(email, db)

    return TokenOut(access_token=auth_data["access_token"], student_id=student["id"])


@router.post("/login", response_model=TokenOut)
async def login_student(payload: LoginIn, db: AsyncPostgrestClient = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()

    try:
        auth_data = sign_in_with_password(email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.") from exc

    result = await db.table("students").select("*").eq("email", email).maybe_single().execute()
    student = result.data if result is not None else None

    if student is not None and bool(student.get("is_synthetic")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Synthetic users cannot log in through this route.",
        )

    await _ensure_profile(auth_data["id"], email, db)

    if student is None:
        student = await _ensure_student(email, db)

    return TokenOut(access_token=auth_data["access_token"], student_id=student["id"])


@router.get("/admin/status", response_model=AdminAccessOut)
async def admin_status(student: dict = Depends(require_admin)) -> AdminAccessOut:
    return AdminAccessOut(allowed=True, email=student["email"])
