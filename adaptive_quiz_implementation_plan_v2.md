
## Database design

### Entities and their reasoning

**Quizzes** — a named collection of questions on a topic. Identified by a slug like `c-interview`. The display name comes from the `topic` column in the source CSV (e.g. `C MCQ (Multiple Choice Questions) - Sanfoundry`).

**Questions** — belongs to exactly one quiz. Uniquely identified by `(quiz_id, question_number)` — a composite primary key, not a standalone UUID. The question_number is the integer from the CSV (1, 2, 3...). Has up to 6 lettered choices (a–f), with e and f nullable. `correct_answer` is stored as a single lowercase character. `difficulty` is NULL on import and filled later by an AI process.

**Students** — real (email + password) or synthetic (email like `sim_001@sim.local`, no password). Same table, distinguished by `is_synthetic`.

**Sessions** — one student taking one quiz. Has `started_at` and `ended_at` (NULL until complete). Owns an ordered sequence of questions (always ascending by question_number).

**Answers** — one row per question per session. Stores `chosen_answer`, `is_correct` (computed server-side), and `response_time_ms`. References a question via `(quiz_id, question_number)`.

### Why composite key instead of UUID per question?

The source CSV identifies questions as `(quiz_id, question_number)`. Using that directly means:
- Import is a straight row-for-row insert with no ID mapping step
- Batch simulation JSON references questions exactly as `{ quiz_id: "c-interview", question_number: 3 }` — matching how the team thinks about them
- No lookup table or translation layer needed anywhere in the system

### Full schema

```sql
CREATE TABLE quizzes (
    id           TEXT        PRIMARY KEY,
    display_name TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE questions (
    quiz_id         TEXT    NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_number INT     NOT NULL,
    question_text   TEXT    NOT NULL,
    choice_a        TEXT    NOT NULL,
    choice_b        TEXT    NOT NULL,
    choice_c        TEXT    NOT NULL,
    choice_d        TEXT    NOT NULL,
    choice_e        TEXT,
    choice_f        TEXT,
    correct_answer  CHAR(1) NOT NULL CHECK (correct_answer IN ('a','b','c','d','e','f')),
    difficulty      TEXT             CHECK (difficulty IN ('easy','medium','hard')),
    PRIMARY KEY (quiz_id, question_number)
);

CREATE TABLE students (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email        TEXT        UNIQUE NOT NULL,
    password_hash TEXT,
    is_synthetic BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sessions (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    quiz_id    TEXT        NOT NULL REFERENCES quizzes(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at   TIMESTAMPTZ
);

CREATE TABLE answers (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    quiz_id         TEXT        NOT NULL,
    question_number INT         NOT NULL,
    chosen_answer   CHAR(1)     NOT NULL CHECK (chosen_answer IN ('a','b','c','d','e','f')),
    is_correct      BOOLEAN     NOT NULL,
    response_time_ms INT        NOT NULL CHECK (response_time_ms > 0 AND response_time_ms < 600000),
    answered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (quiz_id, question_number) REFERENCES questions(quiz_id, question_number)
);

CREATE INDEX idx_answers_session  ON answers(session_id);
CREATE INDEX idx_answers_question ON answers(quiz_id, question_number);
CREATE INDEX idx_sessions_student ON sessions(student_id);
CREATE INDEX idx_sessions_quiz    ON sessions(quiz_id);
```

---

## Backend architecture

### Technology

- **FastAPI** (Python 3.11+) — async request handling, automatic OpenAPI docs
- **SQLAlchemy 2.0** — ORM with typed `Mapped` columns, async sessions via `asyncpg`
- **Alembic** — migrations (run against Supabase PostgreSQL)
- **python-jose** + **bcrypt** — JWT auth and password hashing
- **python-multipart** — multipart file upload parsing
- **Pydantic v2** — request/response validation and serialization

### Folder structure

```
backend/
├── main.py                  # FastAPI app creation, middleware, router registration
├── database.py              # SQLAlchemy engine + async session factory
├── models.py                # ORM models (one class per table)
├── schemas.py               # All Pydantic input/output schemas
├── auth.py                  # JWT creation, verification, get_current_student dependency
├── routers/
│   ├── auth.py              # POST /auth/register, POST /auth/login
│   ├── quizzes.py           # GET /quizzes, GET /quizzes/{quiz_id}
│   ├── sessions.py          # POST /sessions, POST /sessions/{id}/answers, GET /sessions/{id}/result
│   └── admin.py             # All /admin/* routes
├── services/
│   ├── import_service.py    # CSV and JSON parsing + DB insertion logic
│   ├── session_service.py   # Session creation, answer validation, result aggregation
│   └── export_service.py    # CSV streaming for the ML dataset export
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── alembic.ini
├── requirements.txt
└── .env
```

### How the layers relate

```
HTTP Request
    │
    ▼
Router          — validates HTTP method, path, auth header
    │
    ▼
Schema (Pydantic) — validates and deserializes request body
    │
    ▼
Service         — business logic: DB queries, computations, validations
    │
    ▼
Model (SQLAlchemy) — executes SQL against Supabase PostgreSQL
    │
    ▼
Schema (Pydantic) — serializes response, enforces field exclusions
    │
    ▼
HTTP Response
```

The router never touches the DB directly. The service never knows about HTTP. This separation makes each layer independently testable.

### `main.py` responsibilities

- Create the FastAPI app instance
- Register CORS middleware: `allow_origins=["http://localhost:3000"]`, all methods and headers, `allow_credentials=True`
- Register all routers with their prefixes:
  - `auth_router` at `/auth`
  - `quizzes_router` at `/quizzes`
  - `sessions_router` at `/sessions`
  - `admin_router` at `/admin`
- Add a startup event that verifies the DB connection

### `database.py` responsibilities

- Read `DATABASE_URL` from environment
- Create async SQLAlchemy engine using `asyncpg`
- Expose `AsyncSessionLocal` factory
- Expose `get_db` as a FastAPI dependency (yields a session, commits on success, rolls back on exception, always closes)

### `models.py` — one class per table

Use SQLAlchemy 2.0 `DeclarativeBase` and `Mapped` / `mapped_column` syntax. All relationships declared explicitly. The `Quiz` model has a `questions` relationship. The `Session` model has an `answers` relationship. No lazy loading — use `selectinload` explicitly in queries.

### `schemas.py` — the critical schemas

```
# Input schemas (what the client sends)
RegisterIn       { email: str, password: str }
LoginIn          { email: str, password: str }
SessionStartIn   { quiz_id: str }
AnswerIn         { question_number: int, chosen_answer: str, response_time_ms: int }
BulkStudentsIn   { students: list[{ email: str }] }
SimBatchIn       { students: list[SimStudent] }
SimStudent       { student_id: UUID, sessions: list[SimSession] }
SimSession       { quiz_id: str, answers: list[SimAnswer] }
SimAnswer        { question_number: int, chosen_answer: str, response_time_ms: int }
DifficultyIn     { updates: list[{ quiz_id: str, question_number: int, difficulty: str }] }

# Output schemas (what the server sends)
TokenOut         { access_token: str, token_type: str, student_id: UUID }
QuestionOut      { question_number: int, question_text: str,
                   choice_a: str, choice_b: str, choice_c: str, choice_d: str,
                   choice_e: str | None, choice_f: str | None }
                 # correct_answer is NEVER in this schema. Enforce at schema level.
QuizSummaryOut   { id: str, display_name: str, question_count: int }
QuizDetailOut    { id: str, display_name: str, questions: list[QuestionOut] }
SessionStartOut  { session_id: UUID, question: QuestionOut, question_number: int, total: int }
AnswerOut        { done: bool, question: QuestionOut | None,
                   question_number: int | None, total: int | None, session_id: UUID | None }
ResultOut        { total: int, correct: int, accuracy: float,
                   by_difficulty: dict, by_question: list }
ImportOut        { quizzes_created: int, questions_inserted: int, questions_skipped: int }
SimBatchOut      { sessions_created: int, answers_inserted: int, errors: list[str] }
```

### `auth.py` responsibilities

- `hash_password(plain: str) -> str` — bcrypt
- `verify_password(plain: str, hashed: str) -> bool`
- `create_access_token(student_id: UUID) -> str` — JWT, 7-day expiry
- `verify_token(token: str) -> UUID` — decodes JWT, raises `HTTPException(401)` on failure
- `get_current_student` — FastAPI dependency, reads `Authorization: Bearer` header, calls `verify_token`, fetches student from DB, raises `401` if not found

### Router: `auth.py`

**POST `/auth/register`**
- Accept `RegisterIn`
- Check email uniqueness → `400` if taken
- Hash password → insert student with `is_synthetic=False`
- Return `TokenOut`

**POST `/auth/login`**
- Accept `LoginIn`
- Fetch student by email → verify password → `401` if mismatch or student is synthetic (synthetic students cannot log in)
- Return `TokenOut`

### Router: `quizzes.py`

**GET `/quizzes`**
- No auth required
- Query all quizzes, count questions per quiz via subquery
- Return `list[QuizSummaryOut]`

**GET `/quizzes/{quiz_id}`**
- No auth required
- Fetch quiz + all its questions ordered by `question_number` ascending
- Return `QuizDetailOut` — questions as `QuestionOut` (no `correct_answer`)

### Router: `sessions.py`

**POST `/sessions`** *(auth required)*
- Accept `SessionStartIn`
- Verify quiz exists → `404` if not
- Call `session_service.create_session(student_id, quiz_id)`
- Service: insert session row, fetch first question (question_number=1), return session_id + question
- Return `SessionStartOut`

**POST `/sessions/{session_id}/answers`** *(auth required)*
- Accept `AnswerIn`
- Call `session_service.submit_answer(session_id, student_id, answer_in)`
- Service logic:
  1. Fetch session → verify `session.student_id == current_student.id` → `403` if not
  2. Verify `session.ended_at IS NULL` → `400` if already complete
  3. Count existing answers for this session → `expected_question_number = count + 1`
  4. Verify `answer_in.question_number == expected_question_number` → `400` if mismatch
  5. Fetch question → look up `correct_answer` → compute `is_correct`
  6. Validate `response_time_ms` range (1 to 600,000)
  7. Insert answer row
  8. Fetch next question (`question_number = expected + 1`)
  9. If next question exists → return it in `AnswerOut`
  10. If no next question → set `session.ended_at = NOW()`, return `{ done: true, session_id }`
- Return `AnswerOut`

**GET `/sessions/{session_id}/result`** *(auth required)*
- Verify session belongs to student
- Aggregate: total questions, correct count, accuracy, breakdown by difficulty (grouping on question's difficulty), breakdown by question
- Return `ResultOut`

### Router: `admin.py`

All `/admin/*` routes — **no authentication**.

**POST `/admin/import`**
- Accept multipart file upload (`UploadFile`)
- Detect file type by extension or content-type:
  - `.csv` or `text/csv` → parse as CSV
  - `.json` or `application/json` → parse as JSON
- Call `import_service.process_import(rows)` with the parsed rows
- Return `ImportOut`

**POST `/admin/students/synthetic/bulk`**
- Accept `BulkStudentsIn`
- Bulk-insert students with `is_synthetic=True`, `password_hash=NULL`
- Use `ON CONFLICT (email) DO NOTHING`
- Return `[{ email, id }]` for all inserted students

**POST `/admin/simulate/batch`**
- Accept `SimBatchIn`
- Validate: every `student_id` must exist in DB with `is_synthetic=True`
  - Collect all unknown IDs → if any exist, return `400` with the list
- Validate: every `(quiz_id, question_number)` pair must exist in `questions`
  - Collect all unknown pairs → if any exist, return `400` with the list
- For each student → for each session:
  - Insert session row
  - For each answer: look up `correct_answer`, compute `is_correct`, insert answer
  - Set `session.ended_at = NOW()`
- Return `SimBatchOut`

**POST `/admin/questions/difficulty`**
- Accept `DifficultyIn`
- Bulk-update `questions.difficulty` for each `(quiz_id, question_number)` pair
- Return `{ updated: int }`

**GET `/admin/export/answers`**
- Stream CSV using FastAPI `StreamingResponse` with `media_type="text/csv"`
- Header: `Content-Disposition: attachment; filename="responses.csv"`
- Join: `answers → sessions → students` (for `student_id`, `is_synthetic`), `answers → questions` (for `question_text`, `topic` via quiz, `difficulty`)
- Columns: `student_id, quiz_id, question_number, question_text, topic, difficulty, chosen_answer, is_correct, response_time_ms, is_synthetic, answered_at`
- Stream row by row — do not load the full table into memory

### Service: `import_service.py`

This service handles both CSV and JSON input formats. The router detects the format and passes a normalized list of row dicts to `process_import`.

**CSV format** (your Sanfoundry scrape):
```
quiz_id, question, question_text, choice_a, choice_b, choice_c, choice_d, correct, topic
```
Note: the column named `question` in the CSV is the `question_number` (integer). The column named `question_text` is the full question string. Map these explicitly. `correct` maps to `correct_answer`.

**JSON format** — accept two possible structures:

Structure A — array of flat objects matching the CSV shape:
```json
[
  {
    "quiz_id": "c-interview",
    "question": 1,
    "question_text": "Who is the author of C?",
    "choice_a": "James Gosling",
    "choice_b": "Dennis Ritchie",
    "choice_c": "Bjarne Stroustrup",
    "choice_d": "Rasmus Lerdorf",
    "correct": "b",
    "topic": "C MCQ (Multiple Choice Questions) - Sanfoundry"
  }
]
```

Structure B — nested by quiz:
```json
[
  {
    "quiz_id": "c-interview",
    "display_name": "C MCQ (Multiple Choice Questions) - Sanfoundry",
    "questions": [
      {
        "question_number": 1,
        "question_text": "Who is the author of C?",
        "choice_a": "James Gosling",
        "choice_b": "Dennis Ritchie",
        "choice_c": "Bjarne Stroustrup",
        "choice_d": "Rasmus Lerdorf",
        "correct_answer": "b"
      }
    ]
  }
]
```

The service detects which structure it received (check if the top-level array contains objects with a `questions` key) and normalizes both into the same flat row format before inserting.

**Insertion logic:**
1. Collect unique quiz_ids → bulk upsert into `quizzes` with `ON CONFLICT (id) DO NOTHING`
2. For each row → insert into `questions` with `ON CONFLICT (quiz_id, question_number) DO NOTHING`
3. Track counts: quizzes_created, questions_inserted (from `rowcount`), questions_skipped

### Service: `export_service.py`

Implements an async generator that yields CSV rows one at a time. The generator:
1. Yields the header row as a string
2. Opens a DB cursor with server-side iteration (no full table load)
3. Yields each row as a comma-separated string
4. Closes the cursor

The router wraps this generator in `StreamingResponse`.

---

## Frontend architecture

### Technology

- **Next.js 14** with App Router and TypeScript
- **Tailwind CSS** for styling
- **Axios** for HTTP with JWT interceptors
- **next/navigation** for routing

### Folder structure

```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout: font, global styles, metadata
│   ├── page.tsx                      # Redirects to /dashboard or /login
│   ├── (auth)/                       # Route group — no shared layout with main app
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── register/
│   │       └── page.tsx
│   ├── dashboard/
│   │   └── page.tsx
│   ├── quiz/
│   │   └── [sessionId]/
│   │       └── page.tsx
│   ├── result/
│   │   └── [sessionId]/
│   │       └── page.tsx
│   └── admin/
│       ├── layout.tsx                # Admin layout (no nav/header from main app)
│       ├── page.tsx                  # Admin home: tabs for each admin function
│       └── (sections)/
│           ├── import/page.tsx
│           ├── students/page.tsx
│           ├── simulate/page.tsx
│           ├── difficulty/page.tsx
│           └── export/page.tsx
├── components/
│   ├── ui/
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   ├── Toast.tsx
│   │   └── ProgressBar.tsx
│   ├── quiz/
│   │   ├── QuestionCard.tsx          # Question text + choice buttons
│   │   ├── ChoiceButton.tsx          # Single choice option, handles selected state
│   │   ├── QuizTimer.tsx             # Counts up per question, resets on new question
│   │   └── QuizProgress.tsx          # "Question 3 of 20" indicator
│   ├── dashboard/
│   │   ├── QuizCard.tsx              # Quiz display card with name + question count
│   │   └── SessionHistory.tsx        # Table of past sessions
│   └── admin/
│       ├── FileUpload.tsx            # Drag-and-drop file upload for CSV/JSON
│       ├── JsonTextarea.tsx          # Textarea with JSON validation feedback
│       ├── SimulationForm.tsx        # Batch simulation config form
│       └── ExportButton.tsx          # Triggers CSV download
├── lib/
│   ├── api.ts                        # Axios instance + interceptors
│   ├── auth.ts                       # Token read/write/clear helpers
│   └── types.ts                      # TypeScript interfaces matching Pydantic schemas
├── hooks/
│   ├── useQuiz.ts                    # Quiz session state management
│   └── useTimer.ts                   # Per-question timer logic
├── middleware.ts                     # Route protection
├── .env.local
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

### `lib/api.ts` — the HTTP client

```typescript
import axios from 'axios'
import { getToken, clearToken } from './auth'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

### `lib/auth.ts` — token management

```typescript
const TOKEN_KEY = 'quiz_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
  // Also set cookie for Next.js middleware to read
  document.cookie = `token=${token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  document.cookie = 'token=; path=/; max-age=0'
}
```

### `lib/types.ts` — TypeScript interfaces

Define one interface per Pydantic output schema. Keep them in sync with the backend schemas. Key ones:

```typescript
export interface QuestionOut {
  question_number: number
  question_text: string
  choice_a: string
  choice_b: string
  choice_c: string
  choice_d: string
  choice_e: string | null
  choice_f: string | null
}

export interface SessionStartOut {
  session_id: string
  question: QuestionOut
  question_number: number
  total: number
}

export interface AnswerOut {
  done: boolean
  question: QuestionOut | null
  question_number: number | null
  total: number | null
  session_id: string | null
}

export interface QuizSummaryOut {
  id: string
  display_name: string
  question_count: number
}
```

### `middleware.ts` — route protection

```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/login', '/register']

export function middleware(request: NextRequest) {
  const token = request.cookies.get('token')?.value
  const isPublic = PUBLIC_PATHS.some(p => request.nextUrl.pathname.startsWith(p))

  if (!isPublic && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Admin paths are public — no token check
  if (request.nextUrl.pathname.startsWith('/admin')) {
    return NextResponse.next()
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
}
```

### `hooks/useQuiz.ts` — quiz session state

This hook owns all quiz state so the page component stays clean:

```typescript
interface QuizState {
  sessionId: string
  currentQuestion: QuestionOut
  questionNumber: number
  total: number
  selected: string | null   // the chosen letter: 'a' | 'b' | 'c' | 'd' | 'e' | 'f' | null
  submitting: boolean
  done: boolean
}
```

Exposes:
- `state: QuizState`
- `selectAnswer(letter: string): void` — sets `selected`
- `confirmAnswer(responseTimeMs: number): Promise<void>` — POSTs to API, updates state
- `questionRenderTime: number` — timestamp set when `currentQuestion` changes, used to compute response time

### `hooks/useTimer.ts` — per-question timer

Takes `resetTrigger: number` (changes whenever a new question is displayed). Uses `setInterval` to increment elapsed seconds. Clears interval on unmount.

```typescript
export function useTimer(resetTrigger: number): number {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    setElapsed(0)
    const interval = setInterval(() => setElapsed(s => s + 1), 1000)
    return () => clearInterval(interval)
  }, [resetTrigger])

  return elapsed
}
```

### Page: `/quiz/[sessionId]`

This is the most important page. Detailed implementation:

**On mount:**
1. Read `sessionStorage.getItem('session_start')` → parse as `SessionStartOut`
2. If not found → redirect to `/dashboard` (user navigated directly without starting a session)
3. Initialize `useQuiz` hook with the parsed data
4. Clear `sessionStorage` after reading (don't leave stale data)

**Render logic:**
- Show `QuizProgress` (question_number / total)
- Show `QuizTimer` (reset key = question_number, so it resets when question changes)
- Show `QuestionCard` with current question
- `QuestionCard` renders `ChoiceButton` for each non-null choice (a through f)
- When a choice is selected: show a "Confirm Answer" button
- When "Confirm Answer" is clicked:
  - Compute `response_time_ms = Date.now() - questionRenderTime`
  - Call `confirmAnswer(response_time_ms)`
  - Set `submitting = true` → disable all buttons
- When `done = true` → redirect to `/result/[sessionId]`
- **Never show if the previous answer was correct** — the page is neutral throughout

**`ChoiceButton` component:**
- Props: `{ letter: 'a'|'b'|..., text: string, selected: boolean, disabled: boolean, onSelect: () => void }`
- Shows letter badge + choice text
- Highlighted style when `selected`
- Disabled appearance and no click handler when `disabled`

### Page: `/dashboard`

1. On mount: call `GET /quizzes` → render `QuizCard` for each quiz
2. On quiz card click:
   - Call `POST /sessions` with `{ quiz_id }`
   - Store response in `sessionStorage` as `session_start`
   - Navigate to `/quiz/[session_id]`
3. Also fetch student's past sessions and render `SessionHistory`

### Page: `/result/[sessionId]`

1. On mount: call `GET /sessions/{sessionId}/result`
2. Show: score (e.g. "14 / 20"), accuracy percentage, breakdown by difficulty
3. Show "Take another quiz" button → navigate to `/dashboard`

### Admin pages

Each admin section is a separate page under `/admin/(sections)/`. The admin layout provides a simple tab navigation between sections. No authentication.

**`/admin/import`:**
- `FileUpload` component accepts `.csv` and `.json` files (both must work)
- On file select: POST to `/admin/import` as multipart/form-data
- Show `ImportOut` result as a success toast: "Inserted 120 questions across 3 quizzes. Skipped 5 duplicates."
- Also provide a secondary "paste JSON" option using `JsonTextarea`

**`/admin/students`:**
- Form: textarea for emails (one per line) or JSON array
- On submit: POST to `/admin/students/synthetic/bulk`
- Response: show a table of `{ email, id }` — the IDs to copy into simulation scripts

**`/admin/simulate`:**
- `JsonTextarea` with syntax highlighting hint and format example shown inline
- Validate JSON client-side before submitting (parse, show errors immediately)
- On submit: POST to `/admin/simulate/batch`
- Show result: `{ sessions_created, answers_inserted, errors }`
- If errors list is non-empty, display each error message

**`/admin/difficulty`:**
- `JsonTextarea` for the difficulty update payload
- On submit: POST to `/admin/questions/difficulty`
- Show `{ updated: N }` result

**`/admin/export`:**
- Single button: "Download Dataset CSV"
- On click: `window.location.href = NEXT_PUBLIC_API_URL + '/admin/export/answers'`
- The browser handles the file download directly — no JS file handling needed

---

## File import: full logic

The import endpoint at `POST /admin/import` accepts a multipart file upload. It must handle both CSV and JSON seamlessly.

### Detecting format

```python
async def import_file(file: UploadFile):
    filename = file.filename or ""
    content = await file.read()

    if filename.endswith(".csv") or file.content_type == "text/csv":
        rows = parse_csv(content)
    elif filename.endswith(".json") or file.content_type == "application/json":
        rows = parse_json(content)
    else:
        # Try JSON first, fall back to CSV
        try:
            rows = parse_json(content)
        except Exception:
            rows = parse_csv(content)

    return await import_service.process_import(rows)
```

### CSV parsing

```python
import csv, io

def parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")  # handle BOM from Excel exports
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append({
            "quiz_id":         row["quiz_id"].strip(),
            "question_number": int(row["question"].strip()),
            "question_text":   row["question_text"].strip(),  # adjust if column name differs
            "choice_a":        row["choice_a"].strip(),
            "choice_b":        row["choice_b"].strip(),
            "choice_c":        row["choice_c"].strip(),
            "choice_d":        row["choice_d"].strip(),
            "choice_e":        row.get("choice_e", "").strip() or None,
            "choice_f":        row.get("choice_f", "").strip() or None,
            "correct_answer":  row["correct"].strip().lower(),
            "topic":           row["topic"].strip(),
        })
    return rows
```

Note: the CSV column names from your Sanfoundry scrape are `quiz_id`, `question` (number), `question` (text) — look at your actual CSV headers carefully. The column `question` appears twice in the screenshot: once for the number and once for the text. If that is the case, the CSV may actually have `question_number` and `question_text` as separate columns, or the second `question` column might actually be named differently. Inspect the raw CSV headers before writing the parser.

### JSON parsing — two formats

```python
import json

def parse_json(content: bytes) -> list[dict]:
    data = json.loads(content)

    # Detect structure
    if isinstance(data, list) and len(data) > 0 and "questions" in data[0]:
        # Structure B: nested by quiz
        rows = []
        for quiz in data:
            for q in quiz["questions"]:
                rows.append({
                    "quiz_id":         quiz["quiz_id"],
                    "question_number": q["question_number"],
                    "question_text":   q["question_text"],
                    "choice_a":        q["choice_a"],
                    "choice_b":        q["choice_b"],
                    "choice_c":        q["choice_c"],
                    "choice_d":        q["choice_d"],
                    "choice_e":        q.get("choice_e"),
                    "choice_f":        q.get("choice_f"),
                    "correct_answer":  q.get("correct_answer", q.get("correct", "")).lower(),
                    "topic":           quiz.get("display_name", quiz["quiz_id"]),
                })
        return rows
    else:
        # Structure A: flat array matching CSV shape
        rows = []
        for row in data:
            rows.append({
                "quiz_id":         row["quiz_id"],
                "question_number": int(row.get("question_number", row.get("question"))),
                "question_text":   row["question_text"],
                "choice_a":        row["choice_a"],
                "choice_b":        row["choice_b"],
                "choice_c":        row["choice_c"],
                "choice_d":        row["choice_d"],
                "choice_e":        row.get("choice_e"),
                "choice_f":        row.get("choice_f"),
                "correct_answer":  row.get("correct_answer", row.get("correct", "")).lower(),
                "topic":           row.get("topic", row["quiz_id"]),
            })
        return rows
```

---

## Batch simulation payload: the complete format

The team writes this JSON manually and POSTs it to `/admin/simulate/batch`.

```json
{
  "students": [
    {
      "student_id": "uuid-of-sim_001-from-registration",
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
            { "question_number": 1, "chosen_answer": "d", "response_time_ms": 9300 },
            { "question_number": 2, "chosen_answer": "b", "response_time_ms": 7800 }
          ]
        }
      ]
    },
    {
      "student_id": "uuid-of-sim_002-from-registration",
      "sessions": [
        {
          "quiz_id": "c-interview",
          "answers": [
            { "question_number": 1, "chosen_answer": "a", "response_time_ms": 15000 },
            { "question_number": 2, "chosen_answer": "c", "response_time_ms": 22000 }
          ]
        }
      ]
    }
  ]
}
```

A student can have multiple sessions across multiple quizzes in one payload. A student can also appear multiple times across multiple batch submissions — the system will create a new session each time, which is intentional (multiple attempts are valid training data).

---

## Environment variables

**`backend/.env`**
```
DATABASE_URL=postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres
SECRET_KEY=replace-with-64-char-random-hex-string
```

**`frontend/.env.local`**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Supabase connection

Use the **direct connection string** (not the pooler) for SQLAlchemy with asyncpg. Find it in Supabase dashboard → Settings → Database → Connection string → URI tab. Use the `postgresql+asyncpg://` prefix.

Do not use Supabase's JS client, PostgREST API, or Supabase Auth. This platform uses Supabase purely as a hosted PostgreSQL instance. All auth is handled by the FastAPI backend with JWT.

Run the schema SQL in Supabase dashboard → SQL Editor. No Alembic migration needed if the schema is created manually there first.

---

## Invariants the agent must never violate

1. `correct_answer` never appears in any HTTP response. Not in any schema. Not in any log line.
2. `is_correct` is always computed server-side by comparing `chosen_answer` to the stored `correct_answer`. Never derived from client input.
3. `response_time_ms` from real users must be validated: positive integer, less than 600,000.
4. Batch simulation rejects the entire request if any `student_id` is unknown or not `is_synthetic=True`. Return 400 with the list of bad IDs.
5. Batch simulation rejects the entire request if any `(quiz_id, question_number)` pair does not exist. Return 400 with the list of bad pairs.
6. File import is idempotent: same file uploaded twice produces no duplicates. Use `ON CONFLICT DO NOTHING`.
7. Synthetic students cannot log in. The `/auth/login` endpoint must check `is_synthetic` and return 401 if true.
8. The quiz page never reveals whether an answer was correct until the session ends.
9. Question order in real sessions is always ascending by `question_number`. No shuffling.
10. `difficulty` is nullable. Nothing crashes on NULL difficulty anywhere — API, frontend, CSV export.
11. Admin routes have zero authentication. Intentional.
12. Choice buttons (a–f) are rendered dynamically. Never assume exactly 4 choices. Render only non-null choices.

---

## Build order

1. Supabase: paste schema SQL into dashboard SQL editor, run it, verify all tables and indexes exist
2. Backend skeleton: `main.py`, `database.py`, verify DB connection with a test query
3. SQLAlchemy models in `models.py`
4. Pydantic schemas in `schemas.py`
5. Auth: `auth.py` utilities + `/auth/register` + `/auth/login` — test with curl
6. Import endpoint + both parsers (CSV and JSON) — test with your actual Sanfoundry file
7. Quiz endpoints: GET /quizzes, GET /quizzes/{id} — test with curl
8. Session endpoints: POST /sessions, POST /sessions/{id}/answers, GET /sessions/{id}/result — test the full loop with curl
9. Admin endpoints: synthetic students bulk, simulate/batch, difficulty update — test each with curl
10. Export endpoint: verify CSV output has correct columns and joins
11. Frontend: Next.js project setup, Tailwind, axios client, auth helpers, middleware
12. Frontend: login and register pages — verify token is stored and cookie is set
13. Frontend: dashboard — quiz list and session history
14. Frontend: quiz page — the complete one-question-at-a-time flow with timer and progress
15. Frontend: result page
16. Frontend: admin panel with all five sections

Each numbered step must work end-to-end before starting the next. Steps 1–10 (backend) must be fully verified with curl or Postman before writing any frontend code.
