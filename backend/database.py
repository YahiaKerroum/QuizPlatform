import os
from pathlib import Path

from dotenv import load_dotenv
from postgrest import AsyncPostgrestClient

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not set.")
if not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY is not set.")


def _make_client(auth_token: str, api_key: str) -> AsyncPostgrestClient:
    return AsyncPostgrestClient(
        f"{SUPABASE_URL}/rest/v1",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {auth_token}",
        },
    )


def get_admin_db() -> AsyncPostgrestClient:
    """Service-role client — bypasses RLS. Use for admin routes."""
    return _make_client(SUPABASE_SERVICE_KEY, SUPABASE_SERVICE_KEY)


def get_user_db(user_token: str) -> AsyncPostgrestClient:
    """User-JWT client — respects RLS. Use for student routes."""
    return _make_client(user_token, SUPABASE_ANON_KEY)


async def get_db() -> AsyncPostgrestClient:
    """Default dependency — service-role client (admin routes, public reads)."""
    return get_admin_db()


async def verify_database_connection() -> None:
    try:
        await get_admin_db().table("profiles").select("*").limit(1).execute()
    except Exception as exc:
        print(f"Supabase connection check failed: {exc}")
