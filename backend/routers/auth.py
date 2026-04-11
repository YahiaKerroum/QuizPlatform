from fastapi import APIRouter, Depends, HTTPException, status
from postgrest import AsyncPostgrestClient

from ..auth import ensure_profile_for_user, get_current_user_info
from ..database import get_db
from ..schemas import AuthMeOut, LoginIn, RegisterIn, TokenOut
from ..supabase_auth import get_user_from_token, sign_in_with_password, sign_up_with_password

router = APIRouter()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register_student(payload: RegisterIn, db: AsyncPostgrestClient = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    existing = await db.table("students").select("id").eq("email", email).maybe_single().execute()
    if existing.data is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    try:
        sign_up_data = sign_up_with_password(email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    access_token = sign_up_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration succeeded but no session was issued.",
        )

    try:
        user_data = get_user_from_token(access_token)
        await ensure_profile_for_user(user_data, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not initialize user profile.",
        ) from exc

    student_insert = (
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
    student = student_insert.data[0] if student_insert is not None and student_insert.data else existing.data
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create student record.",
        )

    return TokenOut(
        access_token=access_token,
        student_id=student["id"],
    )


@router.post("/login", response_model=TokenOut)
async def login_student(payload: LoginIn, db: AsyncPostgrestClient = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()

    try:
        login_data = sign_in_with_password(email, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc

    access_token = login_data.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    try:
        user_data = get_user_from_token(access_token)
        await ensure_profile_for_user(user_data, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc

    result = await db.table("students").select("*").eq("email", email).maybe_single().execute()
    student = result.data if result is not None else None
    if student is None:
        student_insert = (
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
        student = student_insert.data[0] if student_insert is not None and student_insert.data else None
    elif bool(student.get("is_synthetic")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Synthetic users cannot log in through this route.",
        )

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load student record.",
        )

    return TokenOut(
        access_token=access_token,
        student_id=student["id"],
    )


@router.get("/me", response_model=AuthMeOut)
async def get_auth_me(user_info: dict = Depends(get_current_user_info)) -> AuthMeOut:
    return AuthMeOut.model_validate(user_info)
