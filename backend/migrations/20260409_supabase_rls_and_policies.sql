-- Supabase auth + RLS hardening for quiz platform
-- Apply with supabase migration tooling or the Supabase SQL editor.

-- 1) Enable RLS on user-facing tables
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.answers ENABLE ROW LEVEL SECURITY;

-- 2) Keep catalog read-only for authenticated users
ALTER TABLE public.modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;

-- 3) Drop existing policies if re-running
DROP POLICY IF EXISTS students_self_select ON public.students;
DROP POLICY IF EXISTS sessions_owner_all ON public.sessions;
DROP POLICY IF EXISTS answers_owner_all ON public.answers;
DROP POLICY IF EXISTS modules_read_authenticated ON public.modules;
DROP POLICY IF EXISTS quizzes_read_authenticated ON public.quizzes;
DROP POLICY IF EXISTS questions_read_authenticated ON public.questions;

-- 4) Students can read only their own student row by email
CREATE POLICY students_self_select
ON public.students
FOR SELECT
TO authenticated
USING (lower(email) = lower(auth.email()));

-- 5) Students can fully manage their own sessions
CREATE POLICY sessions_owner_all
ON public.sessions
FOR ALL
TO authenticated
USING (
    student_id IN (
        SELECT s.id
        FROM public.students AS s
        WHERE lower(s.email) = lower(auth.email())
    )
)
WITH CHECK (
    student_id IN (
        SELECT s.id
        FROM public.students AS s
        WHERE lower(s.email) = lower(auth.email())
    )
);

-- 6) Students can fully manage answers bound to their own sessions
CREATE POLICY answers_owner_all
ON public.answers
FOR ALL
TO authenticated
USING (
    session_id IN (
        SELECT se.id
        FROM public.sessions AS se
        JOIN public.students AS st ON st.id = se.student_id
        WHERE lower(st.email) = lower(auth.email())
    )
)
WITH CHECK (
    session_id IN (
        SELECT se.id
        FROM public.sessions AS se
        JOIN public.students AS st ON st.id = se.student_id
        WHERE lower(st.email) = lower(auth.email())
    )
);

-- 7) Users can read and create only their own profile row
-- 7) Authenticated users may read quiz catalog
CREATE POLICY modules_read_authenticated
ON public.modules
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY quizzes_read_authenticated
ON public.quizzes
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY questions_read_authenticated
ON public.questions
FOR SELECT
TO authenticated
USING (true);
