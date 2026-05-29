import os
from pathlib import Path
from postgrest import AsyncPostgrestClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not set.")
if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY is not set.")

def get_supabase_client() -> AsyncPostgrestClient:
    url = f"{SUPABASE_URL}/rest/v1"
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
    }
    return AsyncPostgrestClient(url, headers=headers)

async def get_db() -> AsyncPostgrestClient:
    return get_supabase_client()

async def verify_database_connection() -> None:
    client = get_supabase_client()
    try:
        await client.table("profiles").select("*").limit(1).execute()
    except Exception as e:
        print(f"Supabase connection check failed: {e}")
