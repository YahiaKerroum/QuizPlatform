# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Backend** (run from repo root):
```bash
# Setup
python -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt

# Apply DB schema (first time or after schema changes)
psql -d <db> -f backend/schema.sql

# Run
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# Swagger UI: http://127.0.0.1:8000/docs
```

**Frontend** (from `frontend/`):
```bash
npm install
npm run dev       # http://127.0.0.1:3000
npm run lint
npm run build
```

## Architecture

Two apps: `backend/` (FastAPI + async postgrest → Supabase) and `frontend/` (Next.js 14 App Router). No test suite is checked in.

### Backend

- **`backend/main.py`** — FastAPI app, mounts four routers under `/auth`, `/quizzes`, `/sessions`, `/admin`.
- **`backend/database.py`** — Loads `backend/.env` by explicit path (not CWD). Builds an `AsyncPostgrestClient` from `SUPABASE_URL` + `SUPABASE_SECRET_KEY`. Hard-fails on startup if either is missing.
- **`backend/auth.py`** — JWT creation/verification (7-day tokens, `HS256`). Admin access is controlled by `ADMIN_ALLOWED_EMAILS` env var (comma-separated). `get_current_student` and `require_admin` are FastAPI dependencies.
- **`backend/routers/`** — Thin routers that delegate to services. `admin.py` routes are currently unauthenticated in router wiring.
- **`backend/services/session_service.py`** — Core quiz flow. Non-adaptive mode enforces strict sequential `question_number`; adaptive mode accepts any unanswered question number. `response_time_ms` must be 1–599999.
- **`backend/services/ml_service.py`** — Adaptive question selection. Loads `ML NOTEBOOKS/models/best_model_single_module.pkl` lazily (falls back to rule-based if missing). Exposes `compute_features` (returns a `(1, 21)` ndarray), `predict_level`, `select_next_question`, and `should_stop`. The 21-feature vector order is fixed — changing it breaks the model.

### Frontend

- **`frontend/lib/auth.ts`** — Token stored in both `localStorage` (`quiz_token`) and cookie (`token`). Both must stay in sync; middleware reads the cookie for server-side routing.
- **`frontend/middleware.ts`** — Cookie-based access control. Missing `token` redirects to `/login` for all non-public paths.
- **`frontend/lib/api.ts`** — Axios instance that attaches `Authorization: Bearer <token>` on every request. On 401, clears token and redirects to `/login`. On 403 for `/admin` routes, redirects to `/dashboard`.
- **`frontend/app/`** — App Router pages: `(auth)/login`, `(auth)/register`, `dashboard`, `quiz/[sessionId]`, `result/[sessionId]`, and the `admin/` subtree.

### ML Adaptive System

The adaptive quiz flow:
1. Cold-start: first question is the easiest available (`difficulty = 'easy'`).
2. After each answer, `session_service._submit_adaptive` calls `ml_service.compute_features` on the full answer history, then `predict_level` and `should_stop`.
3. Stop criterion: minimum 8 questions, maximum 20, early stop when model confidence exceeds a session-length-dependent threshold (0.75–0.85).
4. Next question is selected by `select_next_question` which targets a difficulty tier based on current accuracy and error streaks.
5. The six supported module slugs are in `MODULES_ORDER` in `ml_service.py` — unrecognized slugs map to index 0.

### Key Invariants

- Quiz `question_number` values must be contiguous starting at 1.
- Import (`ON CONFLICT DO NOTHING`) skips duplicates on `(quiz_id, question_number)` — re-importing the same CSV is safe but won't update.
- Once a quiz has answer history, questions cannot be added/removed — only content can change.
- Import requires non-empty `choice_a`, `choice_b`, and `correct_answer` in `{a..f}` pointing to a non-empty choice.
- `DATABASE_URL` `postgres://` and `postgresql://` prefixes are normalized to `postgresql+asyncpg://` automatically.

### Env Files

| File | Key vars |
|------|----------|
| `backend/.env` | `DATABASE_URL`, `SECRET_KEY`, `ADMIN_ALLOWED_EMAILS`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY` |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` |
