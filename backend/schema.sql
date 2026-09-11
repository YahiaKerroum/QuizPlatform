-- ============================================================================
-- Adaptive Quiz Platform — full schema bootstrap
--
-- Single source of truth for a brand-new Supabase (or plain Postgres)
-- project: tables, indexes, and Row Level Security in one idempotent script.
-- Run it once against a fresh database (Supabase SQL editor, or
-- `psql -d <db> -f backend/schema.sql`) and the platform is ready for the
-- backend to connect to.
--
-- Safe to re-run: every statement uses IF NOT EXISTS / IF EXISTS /
-- CREATE OR REPLACE so re-applying it against an already-bootstrapped
-- database is a no-op rather than an error.
--
-- `backend/migrations/*.sql` are the historical deltas that produced this
-- schema on the original project -- they're kept for the record, but a new
-- project only needs this one file.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Tables ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quizzes (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    module_id TEXT REFERENCES modules(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
    quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_number INT NOT NULL,
    question_text TEXT NOT NULL,
    question_image_url TEXT,
    choice_a TEXT NOT NULL,
    choice_a_image_url TEXT,
    choice_b TEXT NOT NULL,
    choice_b_image_url TEXT,
    choice_c TEXT,
    choice_c_image_url TEXT,
    choice_d TEXT,
    choice_d_image_url TEXT,
    choice_e TEXT,
    choice_e_image_url TEXT,
    choice_f TEXT,
    choice_f_image_url TEXT,
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('a', 'b', 'c', 'd', 'e', 'f')),
    difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
    PRIMARY KEY (quiz_id, question_number)
);

CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- System of record for authorization roles. Keyed by the Supabase auth
-- user id; email is kept in sync so it can also be joined against
-- `students.email` without a round trip through Supabase Auth.
CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    quiz_id TEXT NOT NULL REFERENCES quizzes(id),
    is_adaptive BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    predicted_level TEXT CHECK (predicted_level IN ('beginner', 'intermediate', 'advanced')),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

CREATE TABLE IF NOT EXISTS answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    quiz_id TEXT NOT NULL,
    question_number INT NOT NULL,
    chosen_answer CHAR(1) NOT NULL CHECK (chosen_answer IN ('a', 'b', 'c', 'd', 'e', 'f')),
    is_correct BOOLEAN NOT NULL,
    response_time_ms INT NOT NULL CHECK (response_time_ms > 0 AND response_time_ms < 600000),
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (quiz_id, question_number) REFERENCES questions(quiz_id, question_number)
);

-- Elo ratings for students (per module) and items -- see
-- backend/services/elo_service.py. Both start at DEFAULT_RATING and update
-- in O(1) after every answer; no retraining, and a sensible signal from the
-- very first response.
CREATE TABLE IF NOT EXISTS student_ratings (
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    rating REAL NOT NULL DEFAULT 1200,
    n_answers INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (student_id, module_id)
);

CREATE TABLE IF NOT EXISTS item_ratings (
    quiz_id TEXT NOT NULL,
    question_number INT NOT NULL,
    rating REAL NOT NULL DEFAULT 1200,
    n_answers INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (quiz_id, question_number),
    FOREIGN KEY (quiz_id, question_number) REFERENCES questions(quiz_id, question_number) ON DELETE CASCADE
);

-- ── Indexes ──────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(quiz_id, question_number);
CREATE INDEX IF NOT EXISTS idx_answers_session_answered_at ON answers(session_id, answered_at);
CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_quiz ON sessions(quiz_id);

-- ============================================================================
-- Row Level Security
--
-- The backend's service-role client (SUPABASE_SECRET_KEY, see
-- backend/database.py:get_admin_db) bypasses RLS entirely and is what admin
-- routes and system operations (student/profile provisioning) use. The
-- policies below govern the user-JWT-scoped client
-- (backend/database.py:get_user_db) used for student-facing session/answer
-- operations, so a leaked or misused student token can't read or write
-- another student's data even if a route forgot to check ownership.
-- ============================================================================

ALTER TABLE modules        ENABLE ROW LEVEL SECURITY;
ALTER TABLE quizzes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE students       ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles       ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE answers        ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_ratings   ENABLE ROW LEVEL SECURITY;

-- Catalog tables: readable by any authenticated user, writable only via the
-- service-role client (admin routes), so no INSERT/UPDATE/DELETE policy.
DROP POLICY IF EXISTS modules_read_authenticated ON modules;
CREATE POLICY modules_read_authenticated
    ON modules FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS quizzes_read_authenticated ON quizzes;
CREATE POLICY quizzes_read_authenticated
    ON quizzes FOR SELECT TO authenticated USING (true);

DROP POLICY IF EXISTS questions_read_authenticated ON questions;
CREATE POLICY questions_read_authenticated
    ON questions FOR SELECT TO authenticated USING (true);

-- profiles: each signed-in user can see and provision only their own row.
DROP POLICY IF EXISTS profiles_own ON profiles;
CREATE POLICY profiles_own
    ON profiles FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- students: a signed-in user can read only the student row matching their
-- own authenticated email (student rows are provisioned server-side by
-- backend/auth.py on first request, so INSERT isn't needed here).
DROP POLICY IF EXISTS students_self_select ON students;
CREATE POLICY students_self_select
    ON students FOR SELECT TO authenticated
    USING (lower(email) = lower(auth.email()));

-- sessions: full CRUD, scoped to the caller's own student row.
DROP POLICY IF EXISTS sessions_owner_all ON sessions;
CREATE POLICY sessions_owner_all
    ON sessions FOR ALL TO authenticated
    USING (
        student_id IN (SELECT s.id FROM students s WHERE lower(s.email) = lower(auth.email()))
    )
    WITH CHECK (
        student_id IN (SELECT s.id FROM students s WHERE lower(s.email) = lower(auth.email()))
    );

-- answers: full CRUD, scoped to sessions owned by the caller.
DROP POLICY IF EXISTS answers_owner_all ON answers;
CREATE POLICY answers_owner_all
    ON answers FOR ALL TO authenticated
    USING (
        session_id IN (
            SELECT se.id FROM sessions se
            JOIN students st ON st.id = se.student_id
            WHERE lower(st.email) = lower(auth.email())
        )
    )
    WITH CHECK (
        session_id IN (
            SELECT se.id FROM sessions se
            JOIN students st ON st.id = se.student_id
            WHERE lower(st.email) = lower(auth.email())
        )
    );

-- student_ratings / item_ratings: written only by the backend's
-- service-role client (after grading an answer), read-only for the owning
-- student otherwise.
DROP POLICY IF EXISTS student_ratings_self_select ON student_ratings;
CREATE POLICY student_ratings_self_select
    ON student_ratings FOR SELECT TO authenticated
    USING (
        student_id IN (SELECT s.id FROM students s WHERE lower(s.email) = lower(auth.email()))
    );

DROP POLICY IF EXISTS item_ratings_read_authenticated ON item_ratings;
CREATE POLICY item_ratings_read_authenticated
    ON item_ratings FOR SELECT TO authenticated USING (true);
