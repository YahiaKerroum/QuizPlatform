# Adaptive Quiz Platform

This repo contains a FastAPI backend and a Next.js frontend for an adaptive quiz platform. The database and auth run entirely on Supabase — no local Postgres install or SQLAlchemy involved. The fastest way to get it running after cloning is:

1. Create a Supabase project and run `backend/schema.sql` once in its SQL editor.
2. Configure the backend and frontend `.env` files with that project's keys.
3. Start the FastAPI backend on port `8000`.
4. Start the Next.js frontend on port `3000`.
5. Import sample quiz data from the admin page.
6. Optionally organize quizzes into modules from the admin catalog.

## Stack

- Backend: FastAPI, `postgrest-py` (`AsyncPostgrestClient`) against Supabase Postgres — no ORM, no direct DB driver
- Auth: Supabase Auth (email/password); the backend verifies the Supabase-issued JWT on every request, it doesn't mint its own
- Frontend: Next.js 14, React 18, Tailwind CSS, `@supabase/supabase-js` for the auth flow

## Project Structure

- `frontend/` — Next.js 14 web application (student dashboard, quiz engine, admin portal)
- `backend/` — FastAPI REST API, service layer, and adaptive session orchestration
- `ai/` — Active learning models (`ai/models/`), training scripts (`ai/training/`), dependencies, and research notebooks (`ai/research/`)
- `data/` — Question bank CSV imports (`data/quizzes/`) and simulation fixtures (`data/simulations/`)
- `docs/` — Feature specifications, logic plans, and implementation guides

## Prerequisites

- Python 3.12 or newer
- Node.js 18 or newer
- A free [Supabase](https://supabase.com) account — no local Postgres needed

Tested locally with:

- Python `3.12.7`
- Node `v22.20.0`

## 1. Clone And Open The Project

```powershell
git clone <your-repo-url>
cd QuizPlatform
```

## 2. Create A Supabase Project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) and create a new project (any region; note the database password, though the backend never uses it directly).
2. Open **Authentication → Providers → Email** and turn **off** "Confirm email" — the backend's sign-up flow expects a session back immediately (see `backend/supabase_auth.py`), which Supabase doesn't return while a confirmation is pending.
3. Open the **SQL Editor**, paste the full contents of [`backend/schema.sql`](backend/schema.sql), and run it. This one file creates every table, index, and Row Level Security policy the backend expects — it's idempotent, so re-running it later after a `git pull` is always safe.
4. Open **Project Settings → API** and note:
   - **Project URL**
   - **anon / publishable key**
   - **service_role / secret key** (never expose this one to the frontend)

## 3. Configure And Start The Backend

Create a virtual environment:

```powershell
py -3.12 -m venv backend/.venv
```

Activate it:

```powershell
.\backend\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run this once for the current terminal and try again:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Install backend dependencies:

```powershell
pip install -r backend/requirements.txt
```

Create the backend env file from the example:

```powershell
Copy-Item backend\.env.example backend\.env
```

Fill in `backend/.env` with the values from step 2. Set `ADMIN_ALLOWED_EMAILS` to your own email so you can reach the admin portal immediately after your first login — it's a bootstrap allowlist; the real system of record is `profiles.role`, which you can hand off to once you have at least one admin.

```env
SUPABASE_URL=https://[your-project-ref].supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxxxxxx
SUPABASE_SECRET_KEY=sb_secret_xxxxxxxxxxxxxxxxx
ADMIN_ALLOWED_EMAILS=you@example.com
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Start the API:

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

If the backend starts correctly, it will be available at:

- `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`

## 4. Configure And Start The Frontend

Open a second terminal in the project root, then run:

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
```

Fill in `frontend/.env.local` with the same project's URL and **publishable** key (never the secret key):

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=https://[your-project-ref].supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxxxxxxxxxxxxxx
```

Start the frontend:

```powershell
npm run dev
```

The app will be available at:

- `http://127.0.0.1:3000`

Admin access checks `profiles.role == 'admin'`, with `ADMIN_ALLOWED_EMAILS` as a bootstrap allowlist (needed because granting the role normally requires already being an admin — see `backend/auth.py:require_admin`):

- Register/log in once through the normal student flow using the email you put in `ADMIN_ALLOWED_EMAILS`
- That email can now reach the admin portal and call `/admin/*` immediately, regardless of `profiles.role`
- Optionally formalize it by setting that profile's `role` to `admin` from the admin portal itself (`/admin/students` → role management, or `PUT /admin/profiles/role`)

## 5. Import Sample Quiz Data

After both servers are running:

1. Open `http://127.0.0.1:3000/admin/import`
2. Upload `data/quizzes/sanfoundry_sample_10_quizzes.csv`
3. Wait for the success message

That sample contains 10 quizzes and is the quickest dataset for local testing.

Notes about the import:

- Duplicate `(quiz_id, question_number)` rows are skipped automatically.
- Some questions only have two answer choices. The backend stores missing choices as `NULL`, and the frontend simply does not render them.
- Image support is URL-based. Supported optional fields are `question_image_url` and `choice_a_image_url` through `choice_f_image_url`.
- Code-like question text and choice text are rendered in code blocks when the frontend detects code content.
- Optional module fields are supported during import: `module_id`, `module_name`, `module_display_name`, or `module`.

## 5B. Organize Quizzes Into Modules

Modules are domain-level groupings such as `C Development`, `Machine Learning`, or `Operating Systems`.

Once quizzes are imported, you can:

1. Open `http://127.0.0.1:3000/admin/catalog`
2. Create a module with an id, display name, and optional description
3. Create a new quiz or open an existing quiz for editing
4. Assign each quiz to a module

The student dashboard uses these modules as browsing sections and filter chips, so students can explore the quiz library by domain instead of scanning one flat list.

## 6. First End-To-End Test

Once the sample import succeeds:

1. Open `http://127.0.0.1:3000/register`
2. Create a normal student account
3. Go to the dashboard
4. Click `Start quiz`
5. Answer questions and finish the quiz
6. Open the result page

Useful pages:

- Student dashboard: `http://127.0.0.1:3000/dashboard`
- Admin catalog: `http://127.0.0.1:3000/admin/catalog`
- Admin import: `http://127.0.0.1:3000/admin/import`
- Admin students: `http://127.0.0.1:3000/admin/students`
- Admin simulation: `http://127.0.0.1:3000/admin/simulate`
- Admin difficulty: `http://127.0.0.1:3000/admin/difficulty`
- Admin export: `http://127.0.0.1:3000/admin/export`

## Optional: Import By API Instead Of The UI

You can import the sample CSV directly through the backend:

```powershell
curl -X POST "http://127.0.0.1:8000/admin/import" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@data/quizzes/sanfoundry_sample_10_quizzes.csv"
```

This requires an `Authorization: Bearer <token>` header for an admin-allowlisted account — grab a token from the browser's dev tools (`localStorage.quiz_token`) after logging in, or add `-H "Authorization: Bearer <token>"`.

## Optional: Create Synthetic Students

The backend includes admin endpoints for bulk synthetic students and batch simulation:

- `POST /admin/students/synthetic/bulk`
- `POST /admin/simulate/batch`

These are useful if you want to seed the platform with AI-style or simulated quiz takers.

## Running The Backend Test Suite

`backend/tests/` covers ML feature/strategy logic, answer shuffling, Elo ratings, and admin auth as pure-function/mocked-dependency tests — no Supabase project or network access required:

```powershell
pip install -r backend/requirements-dev.txt
pytest
```

## Troubleshooting

### Backend fails with `SUPABASE_URL is not set` / `SUPABASE_SECRET_KEY is not set`

Make sure `backend/.env` exists (copied from `backend/.env.example`) and both values are filled in from the Supabase project's **Project Settings → API** page.

### Registration fails with "Registration succeeded but no session was issued"

Email confirmation is still enabled on the Supabase project. Go to **Authentication → Providers → Email** and turn off "Confirm email", or confirm the account via the email Supabase sent before logging in.

### Frontend loads but API requests fail

Make sure:

- The backend is running on `127.0.0.1:8000`
- `frontend/.env.local` points to the same API URL and the same Supabase project as the backend
- You restarted `npm run dev` after changing `.env.local`

### Admin portal / `/admin/*` returns 403

Make sure the email you're logged in as is listed in `ADMIN_ALLOWED_EMAILS` in `backend/.env`, then restart the backend (env vars are read at import time). This is the bootstrap path for the very first admin; afterward, roles can be managed through `profiles.role`.

### `Start quiz` appears broken in dev mode

If the frontend cache gets into a bad state, stop the dev server, remove `.next`, and start it again:

```powershell
Remove-Item -Recurse -Force frontend\.next
cd frontend
npm run dev
```

### `next build` runs out of memory on Windows

If Node crashes during `npm run build`, give it a larger heap for that shell:

```powershell
$env:NODE_OPTIONS="--max-old-space-size=4096"
cd frontend
npm run build
```

### PowerShell cannot activate the virtual environment

Use:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\backend\.venv\Scripts\Activate.ps1
```

## Current Development Notes

- `backend/schema.sql` is the single source of truth for a fresh Supabase project's schema and RLS; `backend/migrations/` is a historical changelog only.
- Admin routes are protected by `profiles.role == 'admin'`, with `ADMIN_ALLOWED_EMAILS` as a bootstrap allowlist for granting the first admin role.
- Modules and quiz assignment are managed from `/admin/catalog`.
- The project includes the larger `data/quizzes/sanfoundry_all_quiz.csv`, but `data/quizzes/sanfoundry_sample_10_quizzes.csv` is the recommended first import after cloning.
