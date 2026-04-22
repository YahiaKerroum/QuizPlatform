# AGENTS.md

## Structure
- Two runnable apps only: `backend/` (FastAPI + async SQLAlchemy) and `frontend/` (Next.js 14 App Router).
- No repo-level task runner, no CI workflows, and no automated tests checked in.

## Fast local runbook
- Backend setup: `python -m venv backend/.venv && source backend/.venv/bin/activate && pip install -r backend/requirements.txt`
- Frontend setup: `cd frontend && npm install`
- Apply DB schema before API start: `psql -d <db> -f backend/schema.sql`
- Run backend from repo root: `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`
- Run frontend: `cd frontend && npm run dev` (script binds to `127.0.0.1`)
- Useful frontend checks: `cd frontend && npm run lint && npm run build`

## Env and startup traps
- Backend loads env from `backend/.env` via explicit path in code (`backend/database.py`, `backend/auth.py`), not from shell CWD.
- Backend hard-fails at import/startup when env is missing required vars (`DATABASE_URL`, `SECRET_KEY`).
- `DATABASE_URL` is normalized in code: `postgres://` and `postgresql://` are converted to `postgresql+asyncpg://`.
- Frontend expects `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`.
- Backend CORS allows only `http://localhost:3000` and `http://127.0.0.1:3000` by default.

## Auth behavior that impacts changes
- `GET/POST /admin/*` routes are currently unauthenticated in backend router wiring.
- Frontend access control is cookie-based middleware (`frontend/middleware.ts`): missing `token` redirects to `/login` for non-public paths.
- Token state is duplicated intentionally: localStorage key `quiz_token` plus cookie `token` (`frontend/lib/auth.ts`); keep both in sync.

## Domain invariants worth preserving
- Session answering is strictly sequential; backend rejects out-of-order `question_number`.
- `response_time_ms` must be `1..599999` (Pydantic + DB check constraint).
- Quiz create/update payloads must use contiguous question numbers starting at `1`.
- Import requires non-empty `choice_a` and `choice_b`; `correct_answer` must be `a..f` and point to a non-empty choice.
- Bulk import upserts with `ON CONFLICT DO NOTHING` on `(quiz_id, question_number)`, so duplicates are skipped, not overwritten.
- Quiz edits are restricted once answer history exists: question numbers cannot be added/removed, only existing content can change.

## High-value code entrypoints
- API composition and route mounts: `backend/main.py`
- Route surfaces: `backend/routers/auth.py`, `backend/routers/quizzes.py`, `backend/routers/sessions.py`, `backend/routers/admin.py`
- Core rules: `backend/services/session_service.py`, `backend/services/catalog_service.py`, `backend/services/import_service.py`, `backend/services/admin_service.py`
- Frontend API/auth glue: `frontend/lib/api.ts`, `frontend/lib/auth.ts`, `frontend/middleware.ts`
