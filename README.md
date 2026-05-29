# Adaptive Quiz Platform

This repo contains a FastAPI backend and a Next.js frontend for an adaptive quiz platform. The fastest way to get it running after cloning is:

1. Start PostgreSQL and create an empty database.
2. Apply the SQL schema from `backend/schema.sql`.
3. Start the FastAPI backend on port `8000`.
4. Start the Next.js frontend on port `3000`.
5. Import sample quiz data from the admin page.
6. Optionally organize quizzes into modules from the admin catalog.

The instructions below follow the setup that was already verified locally.

## Stack

- Backend: FastAPI, SQLAlchemy asyncio, PostgreSQL
- Frontend: Next.js 14, React 18, Tailwind CSS
- Auth: JWT

## Prerequisites

- Python 3.12 or newer
- Node.js 18 or newer
- PostgreSQL 14 or newer
- `psql` available in your terminal

Tested locally with:

- Python `3.12.7`
- Node `v22.20.0`
- PostgreSQL `18.1`

## 1. Clone And Open The Project

```powershell
git clone <your-repo-url>
cd "QUIZ PLATFORM"
```

## 2. Create The Database

Create a local PostgreSQL database. This example uses `quiz_platform_local`.

```powershell
createdb -U postgres quiz_platform_local
```

If `createdb` is not available, create the database in pgAdmin or with:

```powershell
psql -U postgres -c "CREATE DATABASE quiz_platform_local;"
```

Then apply the schema:

```powershell
psql -U postgres -d quiz_platform_local -f backend/schema.sql
```

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

Edit `backend/.env` so it points to your local database. Example:

```env
DATABASE_URL=postgresql+asyncpg://postgres:123456789@127.0.0.1:5432/quiz_platform_local
SECRET_KEY=replace-this-with-a-long-random-secret
ADMIN_ALLOWED_EMAILS=admin1@example.com,admin2@example.com
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

Make sure `frontend/.env.local` contains:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start the frontend:

```powershell
npm run dev
```

The app will be available at:

- `http://127.0.0.1:3000`

Admin access now uses an email allowlist from the backend environment:

- Log in through the normal student login page
- The backend checks whether the logged-in email appears in `ADMIN_ALLOWED_EMAILS`
- Only those emails can use the admin portal or call `/admin/*`

## 5. Import Sample Quiz Data

After both servers are running:

1. Open `http://127.0.0.1:3000/admin/import`
2. Upload `sanfoundry_sample_10_quizzes.csv`
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

## Demo Accounts

If you want to log in immediately on a local setup that already has seeded users, these demo accounts are available:

- `demo.student@example.com` / `Password123!`
- `demo.student2@example.com` / `Password123!`
- `resultfix.20260329@example.com` / `Password123!`

Synthetic AI accounts may also exist in the database, but they do not have passwords and cannot be used through the normal login form.

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
  -F "file=@sanfoundry_sample_10_quizzes.csv"
```

## Optional: Create Synthetic Students

The backend includes admin endpoints for bulk synthetic students and batch simulation:

- `POST /admin/students/synthetic/bulk`
- `POST /admin/simulate/batch`

These are useful if you want to seed the platform with AI-style or simulated quiz takers.

## Troubleshooting

### Backend fails with `DATABASE_URL is not set`

Make sure `backend/.env` exists and contains a valid `DATABASE_URL`.

### Backend cannot connect to PostgreSQL

Check:

- PostgreSQL is running
- The database exists
- Username, password, host, and port are correct
- `backend/schema.sql` has already been applied

### Frontend loads but API requests fail

Make sure:

- The backend is running on `127.0.0.1:8000`
- `frontend/.env.local` points to the same URL
- You restarted `npm run dev` after changing `.env.local`

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

- Admin routes are protected by an env-backed allowed-email list.
- The quickest verified local workflow is PostgreSQL + `backend/schema.sql` + sample CSV import.
- Modules and quiz assignment are managed from `/admin/catalog`.
- The project includes the larger `sanfoundry_all_quiz.csv`, but `sanfoundry_sample_10_quizzes.csv` is the recommended first import after cloning.
