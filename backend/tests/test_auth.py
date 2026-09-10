import pytest
from fastapi import HTTPException

from backend import auth as auth_module

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, role: str | None):
        self._role = role

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    async def execute(self):
        if self._role is None:
            return _FakeResponse(None)
        return _FakeResponse({"role": self._role})


class _FakeDb:
    def __init__(self, role: str | None):
        self._role = role

    def table(self, _name):
        return _FakeQuery(self._role)


async def test_require_admin_allows_profile_role_admin(monkeypatch):
    monkeypatch.setattr(auth_module, "ADMIN_ALLOWED_EMAILS", set())
    monkeypatch.setattr(auth_module, "get_admin_db", lambda: _FakeDb("admin"))

    student = await auth_module.require_admin(student={"email": "prof@example.com"})
    assert student["email"] == "prof@example.com"


async def test_require_admin_rejects_non_admin_profile_role(monkeypatch):
    monkeypatch.setattr(auth_module, "ADMIN_ALLOWED_EMAILS", set())
    monkeypatch.setattr(auth_module, "get_admin_db", lambda: _FakeDb("student"))

    with pytest.raises(HTTPException):
        await auth_module.require_admin(student={"email": "student@example.com"})


async def test_require_admin_rejects_missing_profile(monkeypatch):
    monkeypatch.setattr(auth_module, "ADMIN_ALLOWED_EMAILS", set())
    monkeypatch.setattr(auth_module, "get_admin_db", lambda: _FakeDb(None))

    with pytest.raises(HTTPException):
        await auth_module.require_admin(student={"email": "ghost@example.com"})


async def test_require_admin_bootstrap_allowlist_bypasses_profile_lookup(monkeypatch):
    """The ADMIN_ALLOWED_EMAILS bootstrap path must short-circuit before ever
    touching the database -- otherwise there's no way to grant the first
    admin role, since granting one requires already being an admin."""
    monkeypatch.setattr(auth_module, "ADMIN_ALLOWED_EMAILS", {"bootstrap@example.com"})

    def _boom():
        raise AssertionError("get_admin_db should not be called for a bootstrap-allowlisted email")

    monkeypatch.setattr(auth_module, "get_admin_db", _boom)

    result = await auth_module.require_admin(student={"email": "bootstrap@example.com"})
    assert result["email"] == "bootstrap@example.com"
