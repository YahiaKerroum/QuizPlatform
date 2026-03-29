CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    quiz_id TEXT NOT NULL REFERENCES quizzes(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ
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

CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(quiz_id, question_number);
CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id);
CREATE INDEX IF NOT EXISTS idx_sessions_quiz ON sessions(quiz_id);
