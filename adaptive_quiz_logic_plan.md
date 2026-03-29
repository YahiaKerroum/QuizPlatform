# Adaptive Quiz Platform — Logic Plan & Agent Prompt

Read this entire document before writing a single line of code. It is a reasoning document first, a specification second. Every decision made here is explained. Do not deviate from these decisions without understanding why they were made.

---

## What this system is

A web platform that collects student–question interaction data for an Active Learning ML project. The output is a dataset. Every feature exists to produce clean rows in this table:

```
student_id | quiz_id | question_id | chosen_answer | is_correct | response_time_ms | is_synthetic
```

There are two types of data producers:
- **Real users** who register, log in, and answer quizzes one question at a time
- **Synthetic students** — pre-registered fake accounts whose answers are bulk-inserted via a single JSON payload written manually by the team

There is no AI generation of answers at runtime. No Anthropic API calls during simulation. The team writes the answer scripts themselves and POSTs them.

---

## The database: think before you schema

### What entities exist?

**Quizzes** — a quiz is a named collection of questions on a topic. It is identified by a slug like `c-interview`. It has a display name derived from the `topic` column in the CSV (e.g. `C MCQ (Multiple Choice Questions) - Sanfoundry`). A quiz has many questions.

**Questions** — a question belongs to exactly one quiz. It is uniquely identified by `(quiz_id, question_number)` — not by a standalone ID. The question_number is the integer from the CSV (1, 2, 3...). It has a text body, up to 6 lettered choices (a through f), a correct answer stored as a single letter character, a topic inherited from its quiz, and a difficulty field that starts as NULL and is filled in later by an AI batch process.

**Students** — either real (email + password, registered via the site) or synthetic (pre-registered with emails like `sim_001@sim.local`, `is_synthetic = true`). Both types live in the same table. Synthetic students are created in bulk before any simulation run.

**Sessions** — one session = one student taking one quiz from start to finish. It records when it started and ended. A session belongs to one student and one quiz. A session is complete when `ended_at` is set.

**Answers** — one row per question answered per session. Records: which session, which question (by quiz_id + question_number), what letter the student chose, whether it was correct (computed server-side by comparing to the stored correct letter), and how long they took in milliseconds.

### Why (quiz_id, question_number) and not a UUID per question?

Because your source data identifies questions this way. Inventing a separate UUID per question means you need a lookup table to map your CSV rows to those UUIDs during import and during batch simulation. Using `(quiz_id, question_number)` as a composite key means your import is a direct row-for-row insert, and your batch simulation JSON can reference questions as `{ quiz_id: "c-interview", question_number: 3 }` — exactly as you think about them. Simpler, traceable, no mapping layer needed.

### Where does difficulty live?

On the `questions` table, as a nullable column: `difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')) DEFAULT NULL`. It is NULL on import. An AI batch process fills it later via a dedicated admin endpoint that accepts `[{ quiz_id, question_number, difficulty }]` and bulk-updates the column. The rest of the system functions without it — NULL difficulty is valid during data collection.

---

## The full schema

```sql
-- Supabase: enable UUID extension (already enabled by default)

CREATE TABLE quizzes (
    id TEXT PRIMARY KEY,              -- the slug: 'c-interview', 'python-basics', etc.
    display_name TEXT NOT NULL,       -- full topic string from CSV
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE questions (
    quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_number INT NOT NULL,
    question_text TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT NOT NULL,
    choice_d TEXT NOT NULL,
    choice_e TEXT,                    -- nullable: not all questions have 5 or 6 choices
    choice_f TEXT,
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('a','b','c','d','e','f')),
    difficulty TEXT CHECK (difficulty IN ('easy','medium','hard')),  -- NULL until AI fills it
    PRIMARY KEY (quiz_id, question_number)
);

CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,               -- NULL for synthetic students
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    quiz_id TEXT NOT NULL REFERENCES quizzes(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ             -- NULL until quiz is complete
);

CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    quiz_id TEXT NOT NULL,
    question_number INT NOT NULL,
    chosen_answer CHAR(1) NOT NULL CHECK (chosen_answer IN ('a','b','c','d','e','f')),
    is_correct BOOLEAN NOT NULL,      -- computed server-side, never trusted from client
    response_time_ms INT NOT NULL CHECK (response_time_ms > 0 AND response_time_ms < 600000),
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (quiz_id, question_number) REFERENCES questions(quiz_id, question_number)
);

-- Indexes for the ML export join
CREATE INDEX idx_answers_session ON answers(session_id);
CREATE INDEX idx_answers_question ON answers(quiz_id, question_number);
CREATE INDEX idx_sessions_student ON sessions(student_id);
CREATE INDEX idx_sessions_quiz ON sessions(quiz_id);
```

---

## The CSV import: what needs to happen

Your CSV columns are:
```
quiz_id | question_number | question_text | choice_a | choice_b | choice_c | choice_d | correct | topic
```

Optionally: `choice_e`, `choice_f` if present in some rows.

The import process must:

1. For each unique `quiz_id` in the file, upsert a row into `quizzes` using the `topic` value as `display_name`. Use `ON CONFLICT (id) DO NOTHING` — the quiz already existing is fine.

2. For each row, insert into `questions`. Use `ON CONFLICT (quiz_id, question_number) DO NOTHING` to skip duplicates. Never error on re-import.

3. Map the CSV column name `correct` to the DB column `correct_answer`.

4. `choice_e` and `choice_f` are inserted as NULL if the CSV row doesn't have them.

5. `difficulty` is not in the CSV — it is always inserted as NULL.

The import endpoint accepts either a JSON file or a CSV file upload. The admin uploads the file, the backend parses it, inserts everything, and returns `{ quizzes_created, questions_inserted, questions_skipped }`.

---

## The question flow for real users: why one at a time matters for data quality

When a real user takes a quiz, questions appear one at a time. The user sees a question, picks an answer, confirms, and the next question loads. This is not just a UX choice — it is a data quality choice. It ensures `response_time_ms` is measured per question (not total quiz time split somehow), and it prevents the user from reading ahead and changing earlier answers.

**The flow:**

1. User clicks a quiz on the dashboard → frontend calls `POST /sessions` with `{ quiz_id }` → backend creates a session, determines the question order (sequential: 1, 2, 3...), returns `{ session_id, first_question }` where `first_question` contains the question text and choices but **never the correct answer**.

2. User reads the question, clicks a choice, clicks Confirm → frontend records `response_time_ms = Date.now() - question_render_time`, calls `POST /sessions/{session_id}/answers` with `{ question_number, chosen_answer, response_time_ms }`.

3. Backend looks up `correct_answer` for this question, computes `is_correct`, inserts the answer row, returns the next question or `{ done: true }` if all questions answered.

4. On `done: true`, frontend redirects to the result page which calls `GET /sessions/{session_id}/result`.

**Critical:** `correct_answer` never appears in any API response to the frontend. It is looked up server-side only to compute `is_correct`. The result page shows score after the session ends — not during.

**Answer order validation:** The server tracks how many answers exist for this session. The expected next question_number is `existing_answer_count + 1`. If the submitted question_number doesn't match, reject with 400. This prevents out-of-order submissions and replays.

---

## The batch simulation: the real design

This is not an AI call. This is a bulk data insert triggered by a single HTTP request.

The team manually writes a JSON file like this:

```json
{
  "students": [
    {
      "student_id": "uuid-of-sim_001",
      "sessions": [
        {
          "quiz_id": "c-interview",
          "answers": [
            { "question_number": 1, "chosen_answer": "b", "response_time_ms": 8200 },
            { "question_number": 2, "chosen_answer": "a", "response_time_ms": 12400 },
            { "question_number": 3, "chosen_answer": "c", "response_time_ms": 6100 }
          ]
        },
        {
          "quiz_id": "python-basics",
          "answers": [
            { "question_number": 1, "chosen_answer": "d", "response_time_ms": 9300 }
          ]
        }
      ]
    },
    {
      "student_id": "uuid-of-sim_002",
      "sessions": [ ... ]
    }
  ]
}
```

This file is uploaded to `POST /admin/simulate/batch`. The backend:

1. Validates that every `student_id` exists in the `students` table and has `is_synthetic = true`. Reject with 400 if any unknown student_id appears — this prevents accidental pollution of real student data.

2. Validates that every `(quiz_id, question_number)` pair exists in the `questions` table. Reject with 400 if any unknown question referenced.

3. For each student → for each session → creates a session row → for each answer: looks up `correct_answer` server-side, computes `is_correct`, inserts the answer row.

4. Sets `ended_at` on each session after all its answers are inserted.

5. Returns `{ sessions_created, answers_inserted, errors: [] }`.

**Why reject on unknown student_ids rather than auto-create?** Because the team pre-registers synthetic students deliberately. If an unknown ID appears in the payload, it means a typo or a stale UUID — better to fail loudly than silently insert garbage.

**Why validate question references?** Same reason — a wrong question_number would insert an answer for a question that doesn't exist, corrupting the dataset.

---

## Pre-registering synthetic students

Before any simulation run, the team calls `POST /admin/students/synthetic/bulk` with:

```json
{
  "students": [
    { "email": "sim_001@sim.local" },
    { "email": "sim_002@sim.local" },
    ...
  ]
}
```

The backend inserts them with `is_synthetic = true`, `password_hash = NULL`, and returns `[{ email, id }]` for each created student. The team copies these UUIDs into their batch simulation JSON. This is done once — the IDs are stable and reusable across multiple simulation runs.

---

## Difficulty: the deferred AI fill

After data collection, an admin triggers difficulty assignment. A dedicated endpoint accepts:

```json
POST /admin/questions/difficulty
{
  "updates": [
    { "quiz_id": "c-interview", "question_number": 1, "difficulty": "easy" },
    { "quiz_id": "c-interview", "question_number": 2, "difficulty": "hard" },
    ...
  ]
}
```

This does a bulk UPDATE. The ML dataset export includes whatever is in the `difficulty` column — NULL for questions not yet assigned, or `easy`/`medium`/`hard` for assigned ones.

The AI that generates this payload reads the question text and choices and outputs the JSON above. That is an offline process — it has nothing to do with the platform's runtime.

---

## The ML dataset export

```
GET /admin/export/answers
```

Returns a CSV stream. No pagination — streams the full table. Columns:

```
student_id | quiz_id | question_number | question_text | topic | difficulty |
chosen_answer | is_correct | response_time_ms | is_synthetic | answered_at
```

The join is: `answers → sessions → students` (for `student_id`, `is_synthetic`) and `answers → questions` (for `question_text`, `topic`, `difficulty`). `quiz_id` and `question_number` already live on the `answers` row so no join needed for those.

`difficulty` may be NULL for some rows. The ML team filters as needed.

---

## API contract: the complete list

### Auth
```
POST /auth/register          { email, password } → { access_token, student_id }
POST /auth/login             { email, password } → { access_token, student_id }
```

### Quizzes
```
GET  /quizzes                → [{ id, display_name, question_count }]
GET  /quizzes/{quiz_id}      → { id, display_name, questions: [QuestionOut] }
                               QuestionOut: { question_number, question_text, choice_a..f }
                               Never includes correct_answer.
```

### Sessions (authenticated)
```
POST /sessions               { quiz_id } → { session_id, question: QuestionOut, question_number: 1, total: int }
POST /sessions/{id}/answers  { question_number, chosen_answer, response_time_ms }
                             → { question: QuestionOut, question_number, total }  if not done
                             → { done: true, session_id }                         if complete
GET  /sessions/{id}/result   → { total, correct, accuracy, by_question: [...] }
```

### Admin — no authentication required
```
POST /admin/import                      multipart file upload (CSV or JSON)
                                        → { quizzes_created, questions_inserted, questions_skipped }

POST /admin/students/synthetic/bulk     { students: [{ email }] }
                                        → [{ email, id }]

POST /admin/simulate/batch              { students: [{ student_id, sessions: [...] }] }
                                        → { sessions_created, answers_inserted, errors: [] }

POST /admin/questions/difficulty        { updates: [{ quiz_id, question_number, difficulty }] }
                                        → { updated: int }

GET  /admin/export/answers              → CSV download
```

---

## What the frontend needs

### Pages

**`/login`** and **`/register`** — standard forms. On success, store JWT in localStorage + a cookie named `token` for middleware. Redirect to `/dashboard`.

**`/dashboard`** — calls `GET /quizzes`. Shows quiz cards: name, question count. Click a card → start a session → navigate to `/quiz/[sessionId]`. Also shows the student's past sessions with score.

**`/quiz/[sessionId]`** — the most important page.
- On mount: reads the session start response from `sessionStorage` (stored by dashboard before navigating). Displays the first question.
- Shows question text and choice buttons (a through however many choices exist — render only non-null choices).
- User clicks a choice → it highlights. A "Confirm" button appears.
- On confirm: computes `response_time_ms = Date.now() - questionRenderTime`, POSTs to `/sessions/{id}/answers`, receives next question or `done: true`.
- On `done: true`: redirect to `/result/[sessionId]`.
- Show a progress indicator: `Question 3 of 20`.
- Show a live timer counting up (resets each question). This is for UX only — the actual time is computed in JS, not read from the timer display.
- Never reveal if the previous answer was correct. The page is neutral.

**`/result/[sessionId]`** — calls `GET /sessions/{id}/result`. Shows score, accuracy, breakdown. "Take another quiz" button.

**`/admin`** — two sections:
1. Import: file upload → POST to `/admin/import` → show result toast.
2. Synthetic students: form to bulk-create sim accounts → shows returned IDs.
3. Batch simulation: JSON textarea → POST to `/admin/simulate/batch` → show result.
4. Difficulty update: JSON textarea → POST to `/admin/questions/difficulty`.
5. Export button → triggers CSV download from `/admin/export/answers`.

### Middleware

Protect all routes except `/login` and `/register`. Check for `token` cookie. Redirect to `/login` if missing.

### API client

Axios instance with base URL from `NEXT_PUBLIC_API_URL`. Request interceptor attaches `Authorization: Bearer {token}` from localStorage. Response interceptor: on 401, clear token and redirect to `/login`.

---

## Tech stack

| Concern | Choice |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+ |
| Database | Supabase (PostgreSQL 15) |
| ORM | SQLAlchemy 2.0 with Supabase connection string |
| Migrations | Supabase dashboard SQL editor OR Alembic |
| Auth | JWT (python-jose) + bcrypt |
| File upload | Python `csv` module + `json` module (no extra deps) |
| HTTP client (FE) | Axios |

**Supabase connection:** Use the Supabase project's direct PostgreSQL connection string (not the Supabase REST API — use raw SQL via SQLAlchemy). The connection string format is:
```
postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
```

Do not use Supabase's JavaScript client or PostgREST API. Use it purely as a hosted PostgreSQL instance accessed through SQLAlchemy on the backend.

---

## Environment variables

**`backend/.env`**
```
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
SECRET_KEY=change-this-to-a-long-random-string
```

**`frontend/.env.local`**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Rules the agent must follow

1. **`correct_answer` never leaves the backend.** Not in any response body, not in a log, not in an error message. It is read from the DB only inside the answer-submission handler.

2. **`is_correct` is always computed server-side.** The batch simulation payload sends `chosen_answer`. The backend looks up `correct_answer`, compares, sets `is_correct`. Never trust the client.

3. **`response_time_ms` from real users is validated:** must be a positive integer, must be less than 600,000 (10 minutes). Reject anything outside this range with 400.

4. **Batch simulation rejects unknown student IDs.** Do not auto-create. Do not silently skip. Return a 400 with the list of unknown IDs.

5. **Batch simulation rejects unknown question references.** Same reasoning — fail loudly.

6. **Import is idempotent.** Re-uploading the same CSV twice must not create duplicates. Use `ON CONFLICT DO NOTHING` on both `quizzes` and `questions`.

7. **Choices are rendered dynamically.** The quiz page must not hardcode 4 choices. It renders whatever choices are non-null (a through f). A question with only 4 choices has `choice_e = null` and `choice_f = null` — don't render buttons for those.

8. **Question order in real sessions is always sequential** (question_number 1, 2, 3...). There is no randomization. The order is determined by `question_number` ascending.

9. **`difficulty` is nullable everywhere it appears.** In API responses, in the CSV export, in the frontend. Never crash on a null difficulty.

10. **Admin routes have no authentication.** This is intentional. Do not add auth guards to any `/admin/*` route.

---

## Build order

1. Supabase: run the schema SQL in the dashboard SQL editor. Verify tables exist.
2. Backend: FastAPI skeleton, database connection, SQLAlchemy models matching the schema.
3. Backend: auth endpoints (register, login). Test with curl.
4. Backend: import endpoint. Test by uploading the actual CSV file.
5. Backend: quiz and session endpoints. Test the full answer loop with curl.
6. Backend: admin endpoints (synthetic students, batch simulation, difficulty update, export).
7. Frontend: auth pages, middleware, axios client.
8. Frontend: dashboard and quiz flow (the core user journey).
9. Frontend: result page.
10. Frontend: admin panel.

Each step must be tested before moving to the next. The backend must be fully working via curl/Postman before touching the frontend.
