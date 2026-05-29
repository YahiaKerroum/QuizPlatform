import json
import os
from pathlib import Path
from urllib import error, parse, request

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")


def _require_supabase_env() -> tuple[str, str]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is not set.")
    if not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is not set.")
    return SUPABASE_URL.rstrip("/"), SUPABASE_PUBLISHABLE_KEY


def _request_json(
    method: str,
    path: str,
    payload: dict | None = None,
    bearer_token: str | None = None,
) -> dict:
    base_url, publishable_key = _require_supabase_env()
    url = parse.urljoin(f"{base_url}/", path.lstrip("/"))

    headers = {
        "apikey": publishable_key,
        "Content-Type": "application/json",
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    body: bytes | None = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=body, headers=headers, method=method)

    try:
        with request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {}
        message = data.get("msg") or data.get("error_description") or data.get("error") or "Supabase auth request failed."
        raise ValueError(message) from exc
    except error.URLError as exc:
        raise RuntimeError("Unable to reach Supabase Auth API.") from exc


def sign_up_with_password(email: str, password: str) -> dict:
    return _request_json(
        method="POST",
        path="/auth/v1/signup",
        payload={"email": email, "password": password},
    )


def sign_in_with_password(email: str, password: str) -> dict:
    return _request_json(
        method="POST",
        path="/auth/v1/token?grant_type=password",
        payload={"email": email, "password": password},
    )


def get_user_from_token(token: str) -> dict:
    return _request_json(
        method="GET",
        path="/auth/v1/user",
        bearer_token=token,
    )
