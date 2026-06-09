import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL is not set.")
        if not SUPABASE_ANON_KEY:
            raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is not set.")
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def sign_up_with_password(email: str, password: str) -> dict:
    try:
        response = _get_client().auth.sign_up({"email": email, "password": password})
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    if response.session is None:
        raise ValueError(
            "Registration succeeded but no session was issued. "
            "Disable email confirmation in your Supabase project settings."
        )

    return {
        "access_token": response.session.access_token,
        "id": str(response.user.id),
        "email": response.user.email,
    }


def sign_in_with_password(email: str, password: str) -> dict:
    try:
        response = _get_client().auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    if response.session is None:
        raise ValueError("Login failed — no session returned.")

    return {
        "access_token": response.session.access_token,
        "id": str(response.user.id),
        "email": response.user.email,
    }


def get_user_from_token(token: str) -> dict:
    try:
        response = _get_client().auth.get_user(token)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    if response.user is None:
        raise ValueError("Invalid or expired token.")

    return {
        "id": str(response.user.id),
        "email": response.user.email,
    }
