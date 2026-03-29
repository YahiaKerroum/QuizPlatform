# Adaptive Quiz Platform

This repo contains a FastAPI backend and a Next.js frontend for an adaptive quiz platform. The fastest way to get it running after cloning is:

1. Start PostgreSQL and create an empty database.
2. Apply the SQL schema from `backend/schema.sql`.
3. Start the FastAPI backend on port `8000`.
4. Start the Next.js frontend on port `3000`.
5. Import sample quiz data from the admin page.

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
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@127.0.0.1:5432/quiz_platform_local
SECRET_KEY=replace-this-with-a-long-random-secret
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

## 5. Import Sample Quiz Data

After both servers are running:

1. Open `http://127.0.0.1:3000/admin/import`
2. Upload `sanfoundry_sample_10_quizzes.csv`
3. Wait for the success message

That sample contains 10 quizzes and is the quickest dataset for local testing.

Notes about the import:

- Duplicate `(quiz_id, question_number)` rows are skipped automatically.
- Some questions only have two answer choices. The backend stores missing choices as `NULL`, and the frontend simply does not render them.

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

### PowerShell cannot activate the virtual environment

Use:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\backend\.venv\Scripts\Activate.ps1
```

## Current Development Notes

- Admin routes are currently open for local/demo use.
- The quickest verified local workflow is PostgreSQL + `backend/schema.sql` + sample CSV import.
- The project includes the larger `sanfoundry_all_quiz.csv`, but `sanfoundry_sample_10_quizzes.csv` is the recommended first import after cloning.
