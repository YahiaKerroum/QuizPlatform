import pytest

from backend.services import session_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeSelectQuery:
    """Mimics db.table(x).select(...).eq(...).eq(...).maybe_single().execute()."""

    def __init__(self, row: dict | None):
        self._row = row

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    async def execute(self):
        return _FakeResponse(self._row)


class _FakeUpsertQuery:
    def __init__(self, sink: list):
        self._sink = sink
        self._payload = None

    def upsert(self, payload, **kwargs):
        self._payload = {"payload": payload, **kwargs}
        return self

    async def execute(self):
        self._sink.append(self._payload)
        return _FakeResponse(None)


class _FakeDbOrdered:
    """Simpler double: table() calls happen in a known fixed order for
    _update_elo_ratings (student select, item select, student upsert, item
    upsert), so just pop responses off a queue.
    """

    def __init__(self, student_row, item_row):
        self._queue = [
            _FakeSelectQuery(student_row),
            _FakeSelectQuery(item_row),
        ]
        self.upserts: list = []

    def table(self, _name):
        if self._queue:
            return self._queue.pop(0)
        return _FakeUpsertQuery(self.upserts)


async def test_update_elo_ratings_skips_without_module_id(monkeypatch):
    calls = []
    monkeypatch.setattr(session_service, "get_admin_db", lambda: calls.append("called") or _FakeDbOrdered(None, None))

    await session_service._update_elo_ratings("student-1", None, "quiz-1", 1, True)
    assert calls == []  # never touched the DB


async def test_update_elo_ratings_defaults_to_starting_rating_and_upserts(monkeypatch):
    fake_db = _FakeDbOrdered(student_row=None, item_row=None)
    monkeypatch.setattr(session_service, "get_admin_db", lambda: fake_db)

    await session_service._update_elo_ratings("student-1", "cpp-programming", "quiz-1", 3, True)

    assert len(fake_db.upserts) == 2
    student_upsert, item_upsert = fake_db.upserts
    assert student_upsert["payload"]["student_id"] == "student-1"
    assert student_upsert["payload"]["module_id"] == "cpp-programming"
    assert student_upsert["payload"]["n_answers"] == 1
    assert student_upsert["payload"]["rating"] > 1200  # correct answer from default rating

    assert item_upsert["payload"]["quiz_id"] == "quiz-1"
    assert item_upsert["payload"]["question_number"] == 3
    assert item_upsert["payload"]["n_answers"] == 1
    assert item_upsert["payload"]["rating"] < 1200  # item looked easier than expected


async def test_update_elo_ratings_increments_existing_n_answers(monkeypatch):
    fake_db = _FakeDbOrdered(
        student_row={"rating": 1250.0, "n_answers": 4},
        item_row={"rating": 1180.0, "n_answers": 9},
    )
    monkeypatch.setattr(session_service, "get_admin_db", lambda: fake_db)

    await session_service._update_elo_ratings("student-1", "cpp-programming", "quiz-1", 3, False)

    student_upsert, item_upsert = fake_db.upserts
    assert student_upsert["payload"]["n_answers"] == 5
    assert item_upsert["payload"]["n_answers"] == 10
