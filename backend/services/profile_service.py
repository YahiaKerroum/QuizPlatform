from fastapi import HTTPException, status
from postgrest import AsyncPostgrestClient

from ..schemas import ProfileRoleOut, ProfileRoleSetIn


async def list_profiles(db: AsyncPostgrestClient) -> list[ProfileRoleOut]:
    response = await db.table("profiles").select("email,role").order("created_at").execute()
    profiles = response.data or []
    return [ProfileRoleOut(email=profile["email"], role=profile["role"]) for profile in profiles]


async def set_profile_role(db: AsyncPostgrestClient, payload: ProfileRoleSetIn) -> ProfileRoleOut:
    normalized_email = payload.email.lower().strip()
    result = await db.table("profiles").select("email,role").eq("email", normalized_email).maybe_single().execute()
    profile = result.data
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Ask the user to log in first so a profile row is created.",
        )

    await db.table("profiles").update({"role": payload.role}).eq("email", normalized_email).execute()

    return ProfileRoleOut(email=normalized_email, role=payload.role)
